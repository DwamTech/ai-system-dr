from sqlalchemy import create_engine, inspect, text

from backend.migrations import run_migrations


def test_versioned_migration_upgrades_legacy_tables_once():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE jobs (id VARCHAR(36) PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE tool_executions (job_id VARCHAR(36) PRIMARY KEY)"))
    run_migrations(engine)
    run_migrations(engine)
    with engine.connect() as connection:
        job_columns = {column["name"] for column in inspect(connection).get_columns("jobs")}
        revisions = list(connection.execute(text("SELECT revision FROM schema_migrations")).scalars())
    assert {"max_attempts", "recovery_reason", "error_details"}.issubset(job_columns)
    assert revisions == ["20260906_001_platform_additive"]
