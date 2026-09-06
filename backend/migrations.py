"""Small ordered schema migration runner for existing platform databases.

The project previously relied on ``create_all``.  These revisions make
upgrades auditable and idempotent without introducing a second deployment
tool; a revision is recorded only after every operation commits.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, inspect, text


def _additive_platform_columns(connection) -> None:
    additive_columns = {
        "user_sessions": {"last_seen_at": "TIMESTAMP"},
        "document_versions": {"archive_revision": "INTEGER DEFAULT 0"},
        "messages": {"job_id": "VARCHAR(36)"},
        "jobs": {
            "request_id": "VARCHAR(64)", "deadline_at": "TIMESTAMP",
            "lease_token": "VARCHAR(64)", "lease_expires_at": "TIMESTAMP",
            "max_attempts": "INTEGER DEFAULT 3", "recovery_reason": "VARCHAR(64)",
            "error_code": "VARCHAR(64)", "error_details": "JSON",
        },
        "tool_executions": {
            "tool_revision": "VARCHAR(64) DEFAULT 'tools-v1'", "model_revision": "VARCHAR(255)",
        },
        "outbox": {"lock_token": "VARCHAR(64)", "locked_at": "TIMESTAMP"},
    }
    inspector = inspect(connection)
    for table, columns in additive_columns.items():
        if not inspector.has_table(table):
            continue
        existing = {item["name"] for item in inspector.get_columns(table)}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'))


REVISIONS: tuple[tuple[str, Callable], ...] = (
    ("20260906_001_platform_additive", _additive_platform_columns),
)


def run_migrations(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "revision VARCHAR(64) PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)"
        ))
        applied = set(connection.execute(text("SELECT revision FROM schema_migrations")).scalars())
        for revision, upgrade in REVISIONS:
            if revision in applied:
                continue
            upgrade(connection)
            connection.execute(
                text("INSERT INTO schema_migrations (revision) VALUES (:revision)"),
                {"revision": revision},
            )
