"""Transactionally claim outbox records before publishing them to Celery."""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from backend.celery_app import celery_app
from backend.db import SessionLocal, init_db
from backend.artifacts import ArtifactError, read_tool_result, recover_tool_result
from backend.models import Job, Outbox, ToolExecution

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("platform.dispatcher")
POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "1.5"))
LOCK_SECONDS = int(os.getenv("OUTBOX_LOCK_SECONDS", "60"))
MAX_JOB_ATTEMPTS = int(os.getenv("MAX_JOB_ATTEMPTS", "3"))
TERMINAL_STATUSES = {"cancelled", "completed", "failed"}
RECOVERABLE_STATUSES = {"preparing", "extracting", "indexing", "running", "cancel_requested"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def _complete_saved_tool_result(db, job: Job) -> bool:
    """Close the DB half of a tool result that was saved before a worker died."""
    execution = db.get(ToolExecution, job.id)
    if not execution:
        return False
    if execution.result_storage_key and execution.result_checksum:
        try:
            result = read_tool_result(execution.owner_id, job.id, execution.result_storage_key, execution.result_checksum)
        except ArtifactError:
            return False
    else:
        try:
            recovered = recover_tool_result(execution.owner_id, job.id)
        except ArtifactError:
            return False
        if not recovered:
            return False
        result, digest, size, storage_key = recovered
        execution.result_storage_key = storage_key
        execution.result_checksum = digest
        execution.result_size_bytes = size
        execution.schema_version = str(result.get("schema_version") or execution.schema_version)
    if not result.get("schema_version"):
        return False
    job.status, job.progress = "completed", 100
    job.phase, job.message = "completed", "The saved result was recovered."
    job.finished_at, job.heartbeat_at = now(), now()
    job.lease_token, job.lease_expires_at = None, None
    job.result = {"result_id": job.id, "tool_type": execution.tool_type, "schema_version": result["schema_version"]}
    return True


def recover_expired_jobs() -> int:
    """Requeue abandoned work or move it to a truthful terminal state.

    Celery redelivery can arrive while the former worker's lease is still
    valid.  That redelivery exits safely, so the dispatcher must publish a new
    receipt after the lease expires.  This pass is deliberately DB-backed and
    safe for more than one dispatcher process.
    """
    db = SessionLocal()
    try:
        current = now()
        rows = db.scalars(select(Job).where(
            Job.status.in_(RECOVERABLE_STATUSES),
            or_(Job.lease_expires_at.is_(None), Job.lease_expires_at < current),
        ).order_by(Job.created_at).limit(20).with_for_update(skip_locked=True)).all()
        recovered = 0
        for job in rows:
            if job.status == "cancel_requested":
                job.status, job.phase = "cancelled", "cancelled"
                job.message, job.error_code = "The request was cancelled.", "cancelled"
                job.finished_at, job.lease_token, job.lease_expires_at = current, None, None
                recovered += 1
                continue
            if job.type.startswith("tool_") and _complete_saved_tool_result(db, job):
                recovered += 1
                continue
            maximum = job.max_attempts or MAX_JOB_ATTEMPTS
            if job.attempt >= maximum:
                job.status, job.phase = "failed", "recovery_exhausted"
                job.message, job.error_code = "The worker could not recover this request.", "recovery_exhausted"
                job.finished_at, job.lease_token, job.lease_expires_at = current, None, None
                recovered += 1
                continue
            job.status, job.phase = "queued", "recovering"
            job.message, job.recovery_reason = "Recovering work after an expired worker lease.", "lease_expired"
            job.lease_token, job.lease_expires_at = None, None
            outbox = db.scalar(select(Outbox).where(Outbox.job_id == job.id).with_for_update())
            if outbox:
                outbox.published_at, outbox.lock_token, outbox.locked_at = None, None, None
            recovered += 1
        if recovered:
            db.commit()
            logger.warning("Recovered %s expired jobs", recovered)
        return recovered
    finally:
        db.close()


def dispatch_once() -> int:
    """Claim a batch using SKIP LOCKED; separate dispatchers cannot double-send it."""
    db = SessionLocal()
    token = uuid.uuid4().hex
    try:
        stale = now() - timedelta(seconds=LOCK_SECONDS)
        rows = db.scalars(select(Outbox).where(
            Outbox.published_at.is_(None),
            or_(Outbox.locked_at.is_(None), Outbox.locked_at < stale),
        ).order_by(Outbox.created_at).limit(20).with_for_update(skip_locked=True)).all()
        for item in rows:
            item.lock_token, item.locked_at = token, now()
        db.commit()
        sent = 0
        for item_id in [item.id for item in rows]:
            item = db.get(Outbox, item_id, populate_existing=True)
            if not item or item.lock_token != token or item.published_at:
                continue
            job = db.get(Job, item.job_id)
            if not job or job.status in TERMINAL_STATUSES:
                item.published_at, item.lock_token, item.locked_at = now(), None, None
                db.commit()
                continue
            try:
                # The worker's job lease and unique message receipt make an
                # unavoidable broker redelivery harmless.
                celery_app.send_task(item.task_name, args=[item.job_id], queue=job.queue)
                item.published_at, item.lock_token, item.locked_at = now(), None, None
                item.attempts += 1
                db.commit()
                sent += 1
            except Exception:
                item.attempts, item.lock_token, item.locked_at = item.attempts + 1, None, None
                db.commit()
                logger.exception("Broker unavailable for job %s", item.job_id)
        return sent
    finally:
        db.close()


def main() -> None:
    init_db()
    while True:
        try:
            recover_expired_jobs()
            dispatch_once()
        except Exception:
            logger.exception("Outbox pass failed")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
