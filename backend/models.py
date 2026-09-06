"""Persistent records for public documents and private user work."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user_sessions.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(512))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(1024))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(512))
    storage_key: Mapped[str] = mapped_column(String(1024))
    original_available: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    model_revision: Mapped[str] = mapped_column(String(256))
    chunking_revision: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    expected_chunks: Mapped[int] = mapped_column(Integer, default=0)
    indexed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_revision: Mapped[int] = mapped_column(Integer, default=0)


class DocumentArtifact(Base):
    """The ordered extracted text for one immutable document version."""

    __tablename__ = "document_artifacts"

    version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), default="document-artifact.v1")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user_sessions.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="محادثة جديدة")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "request_id", name="uq_message_request"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    active_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_owner_status", "owner_id", "status"),
        Index("ix_jobs_queue_created", "queue", "created_at"),
        UniqueConstraint("conversation_id", "request_id", name="uq_job_conversation_request"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user_sessions.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    queue: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(255), default="في الانتظار")
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    recovery_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ToolExecution(Base):
    """Private receipt and durable result pointer for a document-tool job."""

    __tablename__ = "tool_executions"
    __table_args__ = (UniqueConstraint("owner_id", "request_id", name="uq_tool_execution_owner_request"),)

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user_sessions.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    tool_type: Mapped[str] = mapped_column(String(32), index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    options_hash: Mapped[str] = mapped_column(String(64))
    tool_revision: Mapped[str] = mapped_column(String(64), default="tools-v1")
    model_revision: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64))
    result_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    result_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class JobSubscription(Base):
    """A private receipt for a shared deduplicated indexing job."""

    __tablename__ = "job_subscriptions"
    __table_args__ = (UniqueConstraint("job_id", "owner_id", name="uq_job_subscription_owner"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user_sessions.id"), index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True, index=True)
    task_name: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
