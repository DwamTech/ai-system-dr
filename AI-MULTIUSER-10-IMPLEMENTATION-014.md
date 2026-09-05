# AI-MULTIUSER-10-IMPLEMENTATION-014

**Date:** 2026-09-05  
**Status:** implemented and container-validated

## Delivered architecture

- FastAPI owns workspace identity, upload receipts, public archive records, private conversations, messages, durable jobs, and an outbox.
- PostgreSQL stores that state. The `task-redis` broker is separate from the existing Redis response cache.
- A dispatcher publishes committed outbox records to Celery. A broker outage therefore does not lose an accepted upload or prompt.
- Indexing has one worker process and its own queue. Generation has a separate worker with concurrency two. Both use late acknowledgement, one prefetched task, heartbeat status, cancellation, and hard time limits.
- One embeddings service loads the multilingual model once and serializes CPU-bound inference. Workers use it remotely instead of loading a model for every browser session.
- Documents are indexed into a staging index with deterministic chunk identifiers. A completed document version is copied to the public index only after indexing succeeds. The public archive is shared; workspace conversations, jobs, cancellation, and messages require the owner token.
- Streamlit now sends upload/index/chat work to the platform API when `PLATFORM_API_URL` is configured. The prior in-process flow remains only as a compatibility fallback when that service is absent.

## Admission limits

| Resource | Limit |
|---|---:|
| Upload | 25 MB PDF, 100 pages |
| Index queue | 30 jobs |
| Generation queue | 80 jobs |
| Index execution | 1 job |
| Generation execution | 2 jobs |
| Embedding execution | 1 model request |

## Required deployment setting

Set a new, random `POSTGRES_PASSWORD` in the untracked `.env` before running Docker Compose. It is intentionally not generated or written into source control. The new keys are listed in `.env.example`.

## Validation performed

- `docker compose config --quiet` passed with a supplied validation password.
- The complete application image built successfully.
- Python compilation and imports for the API, Celery tasks, embeddings client, Streamlit application, and RAG engine passed inside the image.
- A clean PostgreSQL/Redis/API/dispatcher stack accepted ten concurrent workspace conversations. Each prompt was persisted and queued; attempting to read one conversation with another workspace token returned `404`.
- The test containers, volumes, queued messages, and test database were removed after validation.
