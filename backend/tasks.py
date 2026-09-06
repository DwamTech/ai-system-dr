"""Idempotent worker entry points for the shared document archive."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.celery_app import celery_app
from backend.db import SessionLocal
from backend.artifacts import DOCUMENT_SCHEMA, write_document_artifact
from backend.models import Document, DocumentArtifact, DocumentVersion, Job, Message
from backend.tool_runner import run as run_tool_handler
from backend.tooling.common import ToolFailure
from backend.stored_file import StoredFile
from engine_optimized import OptimizedRAGEngine
from processor_optimized import OptimizedDocumentProcessor

logger = logging.getLogger("platform.tasks")
STAGING_INDEX = os.getenv("STAGING_INDEX_NAME", "knowledge_base_staging_v1")
PUBLIC_INDEX = os.getenv("PUBLIC_INDEX_NAME", "knowledge_base_optimized_v2")
LEASE_SECONDS = int(os.getenv("WORKER_LEASE_SECONDS", "240"))
INDEX_LEASE_SECONDS = int(os.getenv("INDEX_WORKER_LEASE_SECONDS", "900"))
TOOL_SOFT_TIME_LIMIT = int(os.getenv("TOOL_SOFT_TIME_LIMIT", "3600"))
TOOL_HARD_TIME_LIMIT = int(os.getenv("TOOL_HARD_TIME_LIMIT", "3660"))
INDEX_SOFT_TIME_LIMIT = int(os.getenv("INDEX_SOFT_TIME_LIMIT", "3600"))
INDEX_HARD_TIME_LIMIT = int(os.getenv("INDEX_HARD_TIME_LIMIT", "3660"))
_engine_lock = threading.Lock()
_shared_engines: dict[str, OptimizedRAGEngine] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def lease_seconds(job: Job) -> int:
    return INDEX_LEASE_SECONDS if job.queue == "indexing" else LEASE_SECONDS


def shared_engine(kind: str) -> OptimizedRAGEngine:
    index = STAGING_INDEX if kind == "staging" else PUBLIC_INDEX
    with _engine_lock:
        if index not in _shared_engines:
            _shared_engines[index] = OptimizedRAGEngine(
                model_name=os.getenv("OPENROUTER_MODEL"), report_errors=False, index_name=index
            )
        return _shared_engines[index]


def claim_job(db, job_id: str) -> tuple[Job | None, str | None]:
    """Acquire a renewable lease so redelivery cannot overwrite a live worker."""
    job = db.get(Job, job_id, with_for_update=True)
    if not job or job.status in {"completed", "failed", "cancelled"}:
        db.rollback()
        return None, None
    current = now()
    if (deadline := as_utc(job.deadline_at)) and deadline <= current:
        job.status, job.phase, job.message, job.finished_at = "failed", "expired", "The worker did not start before the queue deadline.", current
        db.commit()
        return None, None
    if job.status == "cancel_requested":
        job.status, job.phase, job.message, job.finished_at = "cancelled", "cancelled", "The request was cancelled before completion.", current
        db.commit()
        return None, None
    if (lease_until := as_utc(job.lease_expires_at)) and lease_until > current:
        db.rollback()
        return None, None
    token = uuid.uuid4().hex
    job.lease_token, job.lease_expires_at = token, current + timedelta(seconds=lease_seconds(job))
    job.heartbeat_at, job.started_at, job.attempt = current, job.started_at or current, job.attempt + 1
    db.commit()
    return job, token


def still_owned(db, job_id: str, lease_token: str, *, allow_cancel_requested: bool = False) -> Job | None:
    job = db.get(Job, job_id, populate_existing=True)
    blocked = {"cancelled", "failed", "completed"}
    if not allow_cancel_requested:
        blocked.add("cancel_requested")
    if not job or job.lease_token != lease_token or job.status in blocked:
        return None
    return job


def update_job(db, job_id: str, lease_token: str, *, status: str | None = None,
               progress: int | None = None, phase: str | None = None,
               message: str | None = None, result: dict[str, Any] | None = None) -> bool:
    job = still_owned(db, job_id, lease_token)
    if not job:
        db.rollback()
        return False
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = max(0, min(100, int(progress)))
    if phase is not None:
        job.phase = phase
    if message is not None:
        job.message = message
    if result is not None:
        job.result = result
    job.heartbeat_at, job.lease_expires_at = now(), now() + timedelta(seconds=lease_seconds(job))
    if job.status in {"completed", "failed", "cancelled"}:
        job.finished_at = now()
    db.commit()
    return True


def finish_job(
    db, job_id: str, lease_token: str, *, status: str, phase: str, message: str,
    result: dict[str, Any] | None = None, error_code: str | None = None,
    error_details: dict[str, Any] | None = None,
) -> bool:
    """Perform one terminal transition without allowing a cancellation race.

    A progress update deliberately stops when a user requests cancellation, but
    the worker that owns the lease must still be able to acknowledge that
    cancellation.  Keeping this path separate prevents jobs from remaining in
    ``cancel_requested`` forever.
    """
    if status not in {"completed", "failed", "cancelled"}:
        raise ValueError("finish_job only accepts terminal statuses")
    job = db.get(Job, job_id, with_for_update=True)
    if not job or job.lease_token != lease_token:
        db.rollback()
        return False
    if job.status in {"completed", "failed", "cancelled"}:
        db.rollback()
        return job.status == status
    if job.status == "cancel_requested" and status != "cancelled":
        db.rollback()
        return False
    job.status, job.phase, job.message = status, phase, message
    job.progress = 100 if status == "completed" else job.progress
    job.finished_at, job.heartbeat_at = now(), now()
    job.lease_token, job.lease_expires_at = None, None
    if result is not None:
        job.result = result
    if error_code is not None:
        job.error_code = error_code
        job.error_details = error_details or {}
    db.commit()
    return True


@celery_app.task(
    bind=True, name="backend.tasks.run_tool", autoretry_for=(), acks_late=True,
    soft_time_limit=TOOL_SOFT_TIME_LIMIT, time_limit=TOOL_HARD_TIME_LIMIT,
)
def run_tool(self, job_id: str) -> None:
    db = SessionLocal(); lease = None
    try:
        job, lease = claim_job(db, job_id)
        if not job:
            return
        def progress(value: int, phase: str, message: str) -> bool:
            return update_job(db, job.id, lease, status="running", progress=value, phase=phase, message=message)
        result = run_tool_handler(
            db, job, lease, progress,
            lambda prompt, feature: shared_engine("public").llm.invoke(prompt, feature=feature),
        )
        finish_job(db, job.id, lease, status="completed", phase="completed", message="النتيجة جاهزة.", result={"result_id": job.id, "tool_type": job.payload["tool_type"], "schema_version": result["schema_version"]})
    except ToolFailure as exc:
        logger.info("Tool job %s ended with %s", job_id, exc.code)
        if lease:
            finish_job(
                db, job_id, lease, status="cancelled" if exc.code == "cancelled" else "failed",
                phase=exc.code, message=exc.message,
                error_code=exc.code, error_details={},
            )
    except SoftTimeLimitExceeded:
        if lease:
            finish_job(db, job_id, lease, status="failed", phase="provider_timeout", message="انتهت مهلة تنفيذ الأداة.", error_code="provider_timeout")
    except Exception:
        logger.exception("Tool job %s failed", job_id)
        if lease:
            finish_job(db, job_id, lease, status="failed", phase="internal_error", message="تعذر تنفيذ الأداة الآن.", error_code="internal_error")
    finally:
        db.close()


def cancelled(db, job_id: str, lease_token: str) -> bool:
    return still_owned(db, job_id, lease_token) is None


def mark_cancelled(db, job_id: str, lease_token: str | None = None) -> bool:
    job = db.get(Job, job_id, populate_existing=True)
    if not job:
        return False
    if lease_token:
        if not finish_job(db, job_id, lease_token, status="cancelled", phase="cancelled", message="The request was cancelled.", error_code="cancelled"):
            return False
        job = db.get(Job, job_id, populate_existing=True)
    elif job.status == "cancel_requested":
        job.status, job.phase, job.message, job.finished_at = "cancelled", "cancelled", "The request was cancelled.", now()
        job.lease_token, job.lease_expires_at = None, None
        db.commit()
    else:
        return False
    if job.type == "index_document":
        version = db.get(DocumentVersion, job.payload.get("version_id"))
        if version and version.status != "completed":
            version.status = "cancelled"
    db.commit()
    return True


def ensure_public_index(client) -> None:
    if client.indices.exists(index=PUBLIC_INDEX):
        return
    client.indices.create(index=PUBLIC_INDEX, body={
        "settings": {"index": {"knn": True}},
        "mappings": {"dynamic": True, "properties": {
            "vector_field": {"type": "knn_vector", "dimension": int(os.getenv("EMBEDDING_DIMENSION", "384"))},
            "metadata": {"type": "object", "dynamic": True}, "text": {"type": "text"},
        }},
    })


def publish_staged_version(staging: OptimizedRAGEngine, version_id: str, expected_chunks: int) -> None:
    client = staging.get_vectorstore().client
    ensure_public_index(client)
    response = client.reindex(body={
        "source": {"index": STAGING_INDEX, "query": {"term": {"metadata.document_version_id.keyword": version_id}}},
        "dest": {"index": PUBLIC_INDEX, "op_type": "index"}, "conflicts": "proceed",
    }, wait_for_completion=True, refresh=True)
    copied = response.get("created", 0) + response.get("updated", 0)
    if response.get("timed_out") or response.get("failures") or copied != expected_chunks:
        client.delete_by_query(index=PUBLIC_INDEX, body={"query": {"term": {"metadata.document_version_id.keyword": version_id}}},
                               refresh=True, conflicts="proceed", ignore=[404])
        raise RuntimeError("Publishing indexed document version did not copy every chunk")


def published_version_ids(db) -> list[str]:
    return list(db.scalars(select(Document.current_version_id).join(
        DocumentVersion, Document.current_version_id == DocumentVersion.id
    ).where(Document.published.is_(True), DocumentVersion.status == "completed")).all())


@celery_app.task(
    bind=True, name="backend.tasks.index_document", autoretry_for=(), acks_late=True,
    soft_time_limit=INDEX_SOFT_TIME_LIMIT, time_limit=INDEX_HARD_TIME_LIMIT,
)
def index_document(self, job_id: str) -> None:
    db = SessionLocal(); lease = None; version = None
    try:
        job, lease = claim_job(db, job_id)
        if not job:
            return
        payload = job.payload
        version, document = db.get(DocumentVersion, payload["version_id"]), db.get(Document, payload["document_id"])
        if not version or not document or not Path(payload["storage_key"]).is_file():
            raise RuntimeError("The queued document record or original upload is unavailable")
        version.status = "preparing"; db.commit()
        if not update_job(db, job_id, lease, status="preparing", progress=2, phase="preparing", message="Preparing the document."):
            return
        processor = OptimizedDocumentProcessor(chunk_size=int(payload.get("chunk_size", 2000)), chunk_overlap=int(payload.get("chunk_overlap", 300)), reporter=lambda level, message: logger.info("%s: %s", level, message))
        def extraction_progress(stage: str, done: int, total: int) -> None:
            update_job(db, job_id, lease, status="extracting", progress=10 + int(40 * done / max(total, 1)), phase="ocr" if stage == "ocr" else "extracting", message=f"Processing page {done}/{total}.")
        update_job(db, job_id, lease, status="extracting", progress=10, phase="extracting", message="Extracting document text.")
        chunks, raw_text, used_ocr, pages = processor.process_single_pdf(
            StoredFile(payload["storage_key"], document.display_name),
            force_ocr=bool(payload.get("force_ocr")), progress_callback=extraction_progress,
        )
        if not chunks:
            raise RuntimeError("No readable text was produced from this PDF")
        normalized_pages = [str(page).strip() for page in pages]
        if not normalized_pages and raw_text.strip():
            normalized_pages = [raw_text.strip()]
        full_text = "\n\n".join(page for page in normalized_pages if page).strip()
        if not full_text:
            raise RuntimeError("No ordered document text was produced from this PDF")
        artifact_payload = {
            "schema_version": DOCUMENT_SCHEMA,
            "document_id": document.id,
            "document_version_id": version.id,
            "display_name": document.display_name,
            "content_hash": document.content_hash,
            "extraction_method": "ocr" if used_ocr else "direct_extraction",
            "used_ocr": bool(used_ocr),
            "full_text": full_text,
            "pages": [
                {
                    "number": number,
                    "text": page,
                    "has_text": bool(page),
                    "char_count": len(page),
                    "word_count": len(page.split()),
                }
                for number, page in enumerate(normalized_pages, 1)
            ],
            "page_count": len(normalized_pages),
            "text_page_count": sum(1 for page in normalized_pages if page),
            "char_count": len(full_text),
            "word_count": len(full_text.split()),
            "created_at": now().isoformat(),
        }
        artifact = db.get(DocumentArtifact, version.id)
        if artifact is None:
            artifact = DocumentArtifact(version_id=version.id, status="pending")
            db.add(artifact)
            db.flush()
        storage_key, artifact_checksum, _ = write_document_artifact(artifact_payload)
        artifact.status = "ready"
        artifact.storage_key = storage_key
        artifact.checksum = artifact_checksum
        artifact.schema_version = DOCUMENT_SCHEMA
        artifact.page_count = len(normalized_pages)
        artifact.char_count = len(full_text)
        artifact.word_count = len(full_text.split())
        artifact.used_ocr = bool(used_ocr)
        artifact.error_code = None
        db.commit()
        if cancelled(db, job_id, lease):
            mark_cancelled(db, job_id, lease); return
        ids = []
        for position, chunk in enumerate(chunks):
            page_number = chunk.metadata.get("page_number")
            if not isinstance(page_number, int) or page_number < 1:
                page_number = int(chunk.metadata.get("page", 0)) + 1
            chunk.metadata.update({
                "document_id": document.id,
                "document_version_id": version.id,
                "source": document.display_name,
                "chunk_index": position,
                "page_number": page_number,
            })
            ids.append(hashlib.sha256(f"{version.id}:{position}".encode()).hexdigest())
        version.status, version.expected_chunks = "indexing", len(chunks); db.commit()
        def index_progress(done: int, total: int) -> None:
            current = db.get(DocumentVersion, version.id)
            if current:
                current.indexed_chunks = done; db.commit()
            update_job(db, job_id, lease, status="indexing", progress=55 + int(40 * done / max(total, 1)), phase="indexing", message=f"Indexing chunks {done}/{total}.")
        if not shared_engine("staging").ingest_documents_bulk([chunks], batch_size=min(32, int(payload.get("batch_size", 32))), progress_callback=index_progress, ids=ids):
            raise RuntimeError("Staging index did not complete")
        if cancelled(db, job_id, lease):
            mark_cancelled(db, job_id, lease); return
        update_job(db, job_id, lease, status="indexing", progress=96, phase="publishing", message="Publishing the complete version.")
        publish_staged_version(shared_engine("staging"), version.id, len(chunks))
        if cancelled(db, job_id, lease):
            mark_cancelled(db, job_id, lease); return
        version, document = db.get(DocumentVersion, version.id), db.get(Document, document.id)
        version.status, version.indexed_chunks, version.published_at = "completed", len(chunks), now()
        document.published, document.current_version_id = True, version.id; db.commit()
        finish_job(db, job_id, lease, status="completed", phase="completed", message="The document is available in the shared archive.", result={"document_id": document.id, "version_id": version.id, "display_name": document.display_name})
    except SoftTimeLimitExceeded:
        if lease: finish_job(db, job_id, lease, status="failed", phase="timeout", message="The indexing time limit was reached.", error_code="provider_timeout")
    except Exception:
        logger.exception("Indexing job %s failed", job_id)
        if version and version.status != "completed": version.status = "failed"; db.commit()
        if version:
            artifact = db.get(DocumentArtifact, version.id)
            if artifact and artifact.status != "ready":
                artifact.status, artifact.error_code = "failed", "content_unavailable"
                db.commit()
        if lease: finish_job(db, job_id, lease, status="failed", phase="failed", message="Indexing could not be completed; no partial version was published.", error_code="internal_error")
    finally:
        db.close()


@celery_app.task(bind=True, name="backend.tasks.generate_answer", autoretry_for=(), acks_late=True)
def generate_answer(self, job_id: str) -> None:
    db = SessionLocal(); lease = None
    try:
        job, lease = claim_job(db, job_id)
        if not job:
            return
        existing = db.scalar(select(Message).where(Message.job_id == job.id))
        if existing:
            finish_job(db, job.id, lease, status="completed", phase="completed", message="The answer is ready.", result={"message_id": existing.id}); return
        update_job(db, job.id, lease, status="running", progress=15, phase="retrieving", message="Searching the shared archive.")
        payload = job.payload
        history = [{"role": row.role, "content": row.content} for row in db.scalars(select(Message).where(Message.conversation_id == job.conversation_id, Message.status == "completed").order_by(Message.created_at.desc()).limit(4)).all()[::-1]]
        if cancelled(db, job.id, lease): mark_cancelled(db, job.id, lease); return
        response, sources = shared_engine("public").query_with_cache(payload["prompt"], chat_history=history, active_document=payload.get("active_document"), active_document_version_id=payload.get("active_version_id"), published_version_ids=published_version_ids(db))
        if cancelled(db, job.id, lease): mark_cancelled(db, job.id, lease); return
        assistant = Message(id=str(uuid.uuid4()), conversation_id=job.conversation_id, role="assistant", content=response, status="completed", sources=sources, active_version_id=payload.get("active_version_id"), job_id=job.id)
        db.add(assistant)
        try: db.commit()
        except IntegrityError:
            db.rollback(); assistant = db.scalar(select(Message).where(Message.job_id == job.id))
            if not assistant: raise
        finish_job(db, job.id, lease, status="completed", phase="completed", message="The answer is ready.", result={"message_id": assistant.id})
    except SoftTimeLimitExceeded:
        if lease: finish_job(db, job_id, lease, status="failed", phase="timeout", message="The answer time limit was reached.", error_code="provider_timeout")
    except Exception:
        logger.exception("Generation job %s failed", job_id)
        if lease: finish_job(db, job_id, lease, status="failed", phase="failed", message="The answer could not be generated. Please retry.", error_code="internal_error")
    finally:
        db.close()
