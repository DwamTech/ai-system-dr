"""HTTP boundary for durable multi-user work.

The UI only owns a random session token.  All durable state, authorization and
task admission live here, so a Streamlit rerun cannot duplicate or lose work.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db import SessionLocal, init_db
from backend.models import (
    Conversation, Document, DocumentVersion, Job, JobSubscription, Message,
    Outbox, Upload, UserSession,
)


MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "100"))
MAX_INDEX_QUEUE = int(os.getenv("MAX_INDEX_QUEUE", "30"))
MAX_GENERATION_QUEUE = int(os.getenv("MAX_GENERATION_QUEUE", "80"))
MAX_OWNER_INDEX_JOBS = int(os.getenv("MAX_OWNER_INDEX_JOBS", "3"))
MAX_OWNER_GENERATION_JOBS = int(os.getenv("MAX_OWNER_GENERATION_JOBS", "1"))
JOB_WAIT_SECONDS = int(os.getenv("JOB_WAIT_SECONDS", "1800"))
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
ADMIN_METRICS_TOKEN = os.getenv("ADMIN_METRICS_TOKEN", "")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/data/uploads"))
MODEL_REVISION = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
CHUNKING_REVISION = os.getenv("CHUNKING_REVISION", "2000-300-v1")

app = FastAPI(title="AI Conference platform", docs_url=None, redoc_url=None)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_expired(value: datetime | None) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= utcnow()


def owner_from_token(
    authorization: str | None = Header(default=None), db: Session = Depends(db_session)
) -> UserSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "A workspace token is required")
    token = authorization[7:].strip()
    if len(token) < 32:
        raise HTTPException(401, "Invalid workspace token")
    owner = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if not owner or is_expired(owner.expires_at):
        raise HTTPException(401, "Unknown workspace token")
    owner.last_seen_at = utcnow()
    db.commit()
    return owner


def active_statuses() -> tuple[str, ...]:
    return ("queued", "preparing", "extracting", "indexing", "running", "cancel_requested")


def admission_lock(db: Session, name: str) -> None:
    """Serialize a capacity check on PostgreSQL without serializing all API work."""
    if db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": name})


def is_job_visible(db: Session, job: Job, owner: UserSession) -> bool:
    if job.owner_id == owner.id:
        return True
    return bool(db.scalar(select(JobSubscription.id).where(
        JobSubscription.job_id == job.id,
        JobSubscription.owner_id == owner.id,
        JobSubscription.cancelled_at.is_(None),
    )))


def add_subscription(db: Session, job: Job, owner: UserSession) -> None:
    existing = db.scalar(select(JobSubscription).where(
        JobSubscription.job_id == job.id, JobSubscription.owner_id == owner.id
    ))
    if existing is None:
        db.add(JobSubscription(id=str(uuid.uuid4()), job_id=job.id, owner_id=owner.id))


def job_payload(job: Job) -> dict:
    return {
        "id": job.id, "type": job.type, "status": job.status, "progress": job.progress,
        "phase": job.phase, "message": job.message, "result": job.result or {},
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "deadline_at": job.deadline_at.isoformat() if job.deadline_at else None,
    }


class WorkspaceRequest(BaseModel):
    token: str | None = Field(default=None, min_length=32, max_length=512)


class JobCreateRequest(BaseModel):
    upload_id: str
    force_ocr: bool = False


class ConversationRequest(BaseModel):
    title: str = Field(default="محادثة جديدة", max_length=255)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    request_id: str = Field(min_length=8, max_length=64)
    active_version_id: str | None = None


@app.on_event("startup")
def startup() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health(db: Session = Depends(db_session)) -> dict:
    return {"status": "ok", "database": bool(db.execute(select(1)).scalar())}


@app.get("/metrics")
def metrics(x_admin_token: str | None = Header(default=None), db: Session = Depends(db_session)) -> dict:
    """Small protected operational view for alerts and capacity decisions."""
    if not ADMIN_METRICS_TOKEN or not x_admin_token or not hmac.compare_digest(x_admin_token, ADMIN_METRICS_TOKEN):
        raise HTTPException(404, "Not found")
    active = active_statuses()
    rows = db.execute(select(Job.queue, Job.status, func.count()).group_by(Job.queue, Job.status)).all()
    counts = {f"{queue}:{status}": count for queue, status, count in rows}
    oldest = db.scalar(select(func.min(Job.created_at)).where(Job.status.in_(active)))
    return {"queues": counts, "oldest_active_at": oldest.isoformat() if oldest else None,
            "active_jobs": sum(count for key, count in counts.items() if key.rsplit(":", 1)[-1] in active)}


@app.post("/workspaces")
def ensure_workspace(payload: WorkspaceRequest, db: Session = Depends(db_session)) -> dict:
    issued_token = payload.token or secrets.token_urlsafe(48)
    token_hash = hash_token(issued_token)
    owner = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if owner is None:
        owner = UserSession(
            id=str(uuid.uuid4()), token_hash=token_hash,
            expires_at=utcnow() + timedelta(days=SESSION_TTL_DAYS), last_seen_at=utcnow(),
        )
        db.add(owner)
        db.commit()
    # The secret is returned only on first issue.  The Streamlit shell stores
    # it in a SameSite browser cookie; it is never put in a shareable URL.
    return {"workspace_id": owner.id, "token": issued_token if payload.token is None else None}


@app.post("/uploads")
def upload_pdf(
    file: UploadFile = File(...), owner: UserSession = Depends(owner_from_token),
    db: Session = Depends(db_session),
) -> dict:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(422, "Only PDF files are accepted")
    temp_path = UPLOAD_DIR / f".{uuid.uuid4()}.upload"
    digest = hashlib.sha256()
    total = 0
    try:
        with temp_path.open("wb") as target:
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "The maximum upload size is 25 MB")
                digest.update(chunk)
                target.write(chunk)
        try:
            from pypdf import PdfReader
            if len(PdfReader(str(temp_path)).pages) > MAX_PDF_PAGES:
                raise HTTPException(422, "The maximum document length is 100 pages")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, "The uploaded file is not a readable PDF") from exc
        content_hash = digest.hexdigest()
        final_path = UPLOAD_DIR / f"{content_hash}.pdf"
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
        else:
            temp_path.replace(final_path)
        upload = Upload(
            id=str(uuid.uuid4()), owner_id=owner.id, original_name=Path(file.filename).name,
            content_hash=content_hash, storage_key=str(final_path), size_bytes=total,
        )
        db.add(upload)
        db.commit()
        return {"id": upload.id, "name": upload.original_name, "size_bytes": total}
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(500, "Could not store the upload") from exc
    finally:
        file.file.close()


@app.post("/indexing-jobs")
def create_indexing_job(
    payload: JobCreateRequest, owner: UserSession = Depends(owner_from_token),
    db: Session = Depends(db_session),
) -> dict:
    admission_lock(db, "indexing-capacity")
    admission_lock(db, f"index-owner:{owner.id}")
    queued = db.scalar(select(func.count()).select_from(Job).where(
        Job.queue == "indexing", Job.status.in_(active_statuses())
    )) or 0
    if queued >= MAX_INDEX_QUEUE:
        raise HTTPException(429, "Indexing queue is full; retry shortly")
    owned_pending = db.scalar(select(func.count()).select_from(Job).where(
        Job.owner_id == owner.id, Job.queue == "indexing", Job.status.in_(active_statuses())
    )) or 0
    if owned_pending >= MAX_OWNER_INDEX_JOBS:
        raise HTTPException(429, "Your indexing queue is full; retry after a running job completes")
    upload = db.scalar(select(Upload).where(Upload.id == payload.upload_id, Upload.owner_id == owner.id))
    if not upload:
        raise HTTPException(404, "Upload not found")
    document = db.scalar(select(Document).where(Document.content_hash == upload.content_hash))
    if document and document.current_version_id:
        version = db.get(DocumentVersion, document.current_version_id)
        if version and version.status == "completed":
            return {"job": None, "document": document_payload(document, version), "deduplicated": True}
        if version and version.status in {"queued", "preparing", "extracting", "indexing"}:
            active_job = db.scalar(select(Job).where(
                Job.type == "index_document", Job.payload["version_id"].as_string() == version.id,
                Job.status.in_(("queued", "preparing", "extracting", "indexing", "cancel_requested")),
            ))
            if active_job:
                add_subscription(db, active_job, owner)
                db.commit()
                return {"job": job_payload(active_job), "deduplicated": True}
    if document is None:
        document = Document(
            id=str(uuid.uuid4()), content_hash=upload.content_hash, display_name=upload.original_name,
            storage_key=upload.storage_key,
        )
        db.add(document)
        db.flush()
    version = DocumentVersion(
        id=str(uuid.uuid4()), document_id=document.id, model_revision=MODEL_REVISION,
        chunking_revision=CHUNKING_REVISION,
    )
    # A replacement must retain its existing public version until publication.
    # New documents have no public version and remain absent from the archive.
    if not document.current_version_id:
        document.current_version_id = version.id
    job = Job(
        id=str(uuid.uuid4()), owner_id=owner.id, type="index_document", queue="indexing",
        status="queued", progress=0, phase="في انتظار عامل الفهرسة",
        deadline_at=utcnow() + timedelta(seconds=JOB_WAIT_SECONDS),
        payload={
            "document_id": document.id, "version_id": version.id, "storage_key": upload.storage_key,
            "force_ocr": payload.force_ocr, "chunk_size": 2000, "chunk_overlap": 300, "batch_size": 32,
        },
    )
    db.add_all([
        version, job,
        JobSubscription(id=str(uuid.uuid4()), job_id=job.id, owner_id=owner.id),
        Outbox(id=str(uuid.uuid4()), job_id=job.id, task_name="backend.tasks.index_document"),
    ])
    try:
        db.commit()
    except IntegrityError:
        # Two users can upload the same PDF at the same instant.  The unique
        # content hash elects one publisher; the other caller joins its job.
        db.rollback()
        existing_document = db.scalar(select(Document).where(Document.content_hash == upload.content_hash))
        if existing_document and existing_document.current_version_id:
            existing_version = db.get(DocumentVersion, existing_document.current_version_id)
            if existing_version and existing_version.status == "completed":
                return {
                    "job": None, "document": document_payload(existing_document, existing_version),
                    "deduplicated": True,
                }
            if existing_version:
                existing_job = db.scalar(select(Job).where(
                    Job.type == "index_document",
                    Job.payload["version_id"].as_string() == existing_version.id,
                    Job.status.in_(("queued", "preparing", "extracting", "indexing", "cancel_requested")),
                ))
                if existing_job:
                    add_subscription(db, existing_job, owner)
                    db.commit()
                    return {"job": job_payload(existing_job), "deduplicated": True}
        raise HTTPException(409, "An equivalent document is being registered; retry shortly")
    return {"job": job_payload(job), "deduplicated": False}


def document_payload(document: Document, version: DocumentVersion) -> dict:
    return {
        "id": document.id, "version_id": version.id, "name": document.display_name,
        "published_at": version.published_at.isoformat() if version.published_at else None,
    }


@app.get("/documents")
def public_documents(
    q: str = "", limit: int = 50, offset: int = 0,
    owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session),
) -> dict:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    query = (
        select(Document, DocumentVersion).join(DocumentVersion, Document.current_version_id == DocumentVersion.id)
        .where(Document.published.is_(True), DocumentVersion.status == "completed")
    )
    if q.strip():
        query = query.where(Document.display_name.ilike(f"%{q.strip()}%"))
    rows = db.execute(
        query.order_by(Document.created_at.desc()).offset(offset).limit(limit + 1)
    ).all()
    return {
        "documents": [document_payload(document, version) for document, version in rows[:limit]],
        "next_offset": offset + limit if len(rows) > limit else None,
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)) -> dict:
    job = db.get(Job, job_id)
    if not job or not is_job_visible(db, job, owner):
        raise HTTPException(404, "Job not found")
    return job_payload(job)


@app.get("/jobs")
def list_jobs(
    limit: int = 50, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)
) -> dict:
    limit = max(1, min(limit, 100))
    subscribed = select(JobSubscription.job_id).where(
        JobSubscription.owner_id == owner.id, JobSubscription.cancelled_at.is_(None)
    )
    jobs = db.scalars(select(Job).where(or_(Job.owner_id == owner.id, Job.id.in_(subscribed)))
                      .order_by(Job.created_at.desc()).limit(limit)).all()
    return {"jobs": [job_payload(job) for job in jobs]}


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)) -> dict:
    job = db.get(Job, job_id)
    if not job or not is_job_visible(db, job, owner):
        raise HTTPException(404, "Job not found")
    subscription = db.scalar(select(JobSubscription).where(
        JobSubscription.job_id == job.id, JobSubscription.owner_id == owner.id
    ))
    active_subscribers = db.scalar(select(func.count()).select_from(JobSubscription).where(
        JobSubscription.job_id == job.id, JobSubscription.cancelled_at.is_(None)
    )) or 0
    if job.owner_id != owner.id or active_subscribers > 1:
        if subscription:
            subscription.cancelled_at = utcnow()
            db.commit()
        return {**job_payload(job), "subscription_cancelled": True}
    if job.status not in {"completed", "failed", "cancelled"}:
        job.status = "cancel_requested"
        job.phase = "جارٍ إلغاء المهمة"
        job.message = "سيوقف العامل المهمة عند نقطة آمنة."
        db.commit()
    return job_payload(job)


@app.post("/conversations")
def create_conversation(
    payload: ConversationRequest, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)
) -> dict:
    conversation = Conversation(id=str(uuid.uuid4()), owner_id=owner.id, title=payload.title)
    db.add(conversation)
    db.commit()
    return {"id": conversation.id, "title": conversation.title}


@app.get("/conversations")
def list_conversations(
    limit: int = 30, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)
) -> dict:
    conversations = db.scalars(select(Conversation).where(Conversation.owner_id == owner.id)
                               .order_by(Conversation.created_at.desc()).limit(max(1, min(limit, 100)))).all()
    return {"conversations": [
        {"id": conversation.id, "title": conversation.title,
         "created_at": conversation.created_at.isoformat() if conversation.created_at else None}
        for conversation in conversations
    ]}


def owned_conversation(db: Session, owner: UserSession, conversation_id: str) -> Conversation:
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id, Conversation.owner_id == owner.id
    ))
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    return conversation


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: str, owner: UserSession = Depends(owner_from_token), db: Session = Depends(db_session)
) -> dict:
    owned_conversation(db, owner, conversation_id)
    messages = db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)).all()
    return {"messages": [
        {"id": message.id, "role": message.role, "content": message.content, "status": message.status,
         "sources": message.sources or [], "request_id": message.request_id}
        for message in messages
    ]}


@app.post("/conversations/{conversation_id}/messages")
def send_prompt(
    conversation_id: str, payload: PromptRequest, owner: UserSession = Depends(owner_from_token),
    db: Session = Depends(db_session),
) -> dict:
    owned_conversation(db, owner, conversation_id)
    admission_lock(db, f"conversation:{conversation_id}")
    admission_lock(db, "generation-capacity")
    admission_lock(db, f"generation-owner:{owner.id}")
    existing = db.scalar(select(Job).where(
        Job.conversation_id == conversation_id, Job.request_id == payload.request_id
    ))
    if existing:
        return {"job": job_payload(existing), "deduplicated": True}
    queued = db.scalar(select(func.count()).select_from(Job).where(
        Job.queue == "generation", Job.status.in_(active_statuses())
    )) or 0
    if queued >= MAX_GENERATION_QUEUE:
        raise HTTPException(429, "Generation queue is full; retry shortly")
    in_conversation = db.scalar(select(func.count()).select_from(Job).where(
        Job.conversation_id == conversation_id, Job.queue == "generation", Job.status.in_(active_statuses())
    )) or 0
    if in_conversation:
        raise HTTPException(409, "This conversation already has a request in progress")
    owned_pending = db.scalar(select(func.count()).select_from(Job).where(
        Job.owner_id == owner.id, Job.queue == "generation", Job.status.in_(active_statuses())
    )) or 0
    if owned_pending >= MAX_OWNER_GENERATION_JOBS:
        raise HTTPException(429, "Your generation queue is full; wait for the current answer")
    active_document = None
    if payload.active_version_id:
        version = db.get(DocumentVersion, payload.active_version_id)
        if not version or version.status != "completed":
            raise HTTPException(422, "Selected document is not available")
        active_document = db.get(Document, version.document_id).display_name
    user_message = Message(
        id=str(uuid.uuid4()), conversation_id=conversation_id, request_id=payload.request_id,
        role="user", content=payload.prompt, status="completed", active_version_id=payload.active_version_id,
    )
    job = Job(
        id=str(uuid.uuid4()), owner_id=owner.id, conversation_id=conversation_id, type="generate_answer",
        queue="generation", status="queued", phase="في انتظار الإجابة", request_id=payload.request_id,
        deadline_at=utcnow() + timedelta(seconds=JOB_WAIT_SECONDS), payload={
            "prompt": payload.prompt, "request_id": payload.request_id,
            "active_version_id": payload.active_version_id, "active_document": active_document,
        },
    )
    db.add_all([user_message, job, Outbox(id=str(uuid.uuid4()), job_id=job.id, task_name="backend.tasks.generate_answer")])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Job).where(
            Job.conversation_id == conversation_id, Job.request_id == payload.request_id
        ))
        if existing:
            return {"job": job_payload(existing), "deduplicated": True}
        raise
    return {"job": job_payload(job), "deduplicated": False}
