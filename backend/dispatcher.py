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
from backend.models import Job, Outbox

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("platform.dispatcher")
POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "1.5"))
LOCK_SECONDS = int(os.getenv("OUTBOX_LOCK_SECONDS", "60"))


def now() -> datetime:
    return datetime.now(timezone.utc)


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
            if not job or job.status in {"cancelled", "completed", "failed"}:
                item.published_at, item.lock_token, item.locked_at = now(), None, None
                db.commit()
                continue
            try:
                # The worker's job lease and unique message receipt make an
                # unavoidable broker redelivery harmless.
                celery_app.send_task(item.task_name, args=[item.job_id])
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
            dispatch_once()
        except Exception:
            logger.exception("Outbox pass failed")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
