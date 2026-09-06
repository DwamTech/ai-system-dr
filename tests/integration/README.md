# Integration tests

These tests run against the Docker services and never print workspace tokens or document text.

`live_job_lifecycle.py` verifies that a queued job reaches `cancelled`, request
IDs are idempotent, and an invalid translation page is rejected before work is
created.
