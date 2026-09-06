from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import dispatcher
from backend.db import Base
from backend.models import Job, Outbox, UserSession
from backend.tasks import finish_job, now, update_job


def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_job(db, *, status="running", expires_in=60, attempt=1, max_attempts=3):
    owner = UserSession(id="owner", token_hash="x", expires_at=now() + timedelta(days=1))
    job = Job(
        id="job", owner_id=owner.id, type="tool_analysis", queue="tools", status=status,
        lease_token="lease", lease_expires_at=now() + timedelta(seconds=expires_in),
        deadline_at=now() + timedelta(minutes=10), attempt=attempt, max_attempts=max_attempts,
    )
    db.add_all([owner, job, Outbox(id="outbox", job_id=job.id, task_name="backend.tasks.run_tool", published_at=now())])
    db.commit()
    return job


def test_cancel_requested_can_finish_as_cancelled():
    factory = session_factory()
    db = factory()
    make_job(db, status="cancel_requested")

    assert not update_job(db, "job", "lease", progress=50, phase="running", message="should stop")
    assert finish_job(
        db, "job", "lease", status="cancelled", phase="cancelled", message="cancelled",
        error_code="cancelled",
    )
    completed = db.get(Job, "job")
    assert completed.status == "cancelled"
    assert completed.finished_at is not None
    assert completed.lease_token is None


def test_cancel_requested_cannot_be_overwritten_by_completed_result():
    factory = session_factory()
    db = factory()
    make_job(db, status="cancel_requested")

    assert not finish_job(db, "job", "lease", status="completed", phase="completed", message="late result")
    assert db.get(Job, "job").status == "cancel_requested"


def test_expired_lease_is_requeued_and_outbox_republished(monkeypatch):
    factory = session_factory()
    setup = factory()
    make_job(setup, expires_in=-1)
    setup.close()
    monkeypatch.setattr(dispatcher, "SessionLocal", factory)

    assert dispatcher.recover_expired_jobs() == 1
    check = factory()
    job, outbox = check.get(Job, "job"), check.get(Outbox, "outbox")
    assert job.status == "queued"
    assert job.phase == "recovering"
    assert job.recovery_reason == "lease_expired"
    assert job.lease_token is None
    assert outbox.published_at is None


def test_expired_job_stops_after_the_attempt_limit(monkeypatch):
    factory = session_factory()
    setup = factory()
    make_job(setup, expires_in=-1, attempt=3, max_attempts=3)
    setup.close()
    monkeypatch.setattr(dispatcher, "SessionLocal", factory)

    assert dispatcher.recover_expired_jobs() == 1
    check = factory()
    job = check.get(Job, "job")
    assert job.status == "failed"
    assert job.error_code == "recovery_exhausted"
