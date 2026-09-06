"""Database setup shared by the API and worker processes."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
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
    from backend.migrations import run_migrations
    run_migrations(engine)
