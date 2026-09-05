"""Database setup shared by the API and worker processes."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/platform.db")


class Base(DeclarativeBase):
    pass


engine_options = {"pool_pre_ping": True, "future": True}
if DATABASE_URL.startswith("sqlite"):
    Path("/app/data").mkdir(parents=True, exist_ok=True)
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def init_db() -> None:
    # Imported lazily to avoid circular model imports at module initialization.
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Deployments made before the multi-user platform used create_all only.
    # Keep upgrades additive so a restart cannot strand their queued jobs.
    additive_columns = {
        "user_sessions": {"last_seen_at": "TIMESTAMP"},
        "document_versions": {"archive_revision": "INTEGER DEFAULT 0"},
        "messages": {"job_id": "VARCHAR(36)"},
        "jobs": {
            "request_id": "VARCHAR(64)", "deadline_at": "TIMESTAMP",
            "lease_token": "VARCHAR(64)", "lease_expires_at": "TIMESTAMP",
        },
        "outbox": {"lock_token": "VARCHAR(64)", "locked_at": "TIMESTAMP"},
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table, columns in additive_columns.items():
            if not inspector.has_table(table):
                continue
            existing = {item["name"] for item in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
