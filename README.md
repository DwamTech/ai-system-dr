# AI Conference Research Assistant

Arabic/English Streamlit application for indexing PDF documents, local OCR and
vector retrieval, then performing academic chat and analysis. The seven existing
tabs cover RAG search, summary, entity extraction, translation, text analysis,
mind maps, and academic web search.

## Architecture

- PDF extraction and OCR remain local (`PyPDFLoader`, `pdf2image`, Tesseract).
- Embeddings remain local and unchanged: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- OpenSearch stores the existing `knowledge_base_optimized_v2` corpus.
- Redis caches RAG responses.
- OpenRouter supplies all LLM generation; no Ollama container is required.

Changing the chat model does not change embeddings or re-index the corpus.

## Local Docker Compose

1. Copy `.env.example` to an untracked `.env` and set `OPENROUTER_API_KEY` and
   `SEARXNG_SECRET`. Do not commit `.env`.
2. Ensure Docker Desktop is running.
3. Run `docker compose up --build`.
4. Open `http://localhost:8502`.

The runtime also starts PostgreSQL, a durable Redis broker, the API,
dispatcher, shared embeddings service, isolated indexing/generation workers,
and separate long/fast tool workers. Internal services are not exposed on the
host. Streamlit, OpenSearch, Redis, and SearXNG bind to `127.0.0.1`; use an
authenticated TLS reverse proxy for a shared deployment.

The archive is public to every workspace. Conversations, tool jobs, saved
results, downloads, and cancellation remain private to the workspace token.
The API rejects excess per-user/global work before it enters the outbox.

## Document tools operations

- Schema upgrades run in revision order when the API starts and are recorded in
  `schema_migrations`.
- Inspect readiness with `docker compose exec -T api curl -fsS http://localhost:8000/ready`.
- Preview artifact backfill with `docker compose exec -T api python -m backend.backfill_artifacts --dry-run --limit 100`.
- Execute backfill by removing `--dry-run`; it skips versions that are already ready.
- Create a consistent database/artifact backup with `powershell -File scripts/backup_platform.ps1`.
- Restore a reviewed backup with `powershell -File scripts/restore_platform.ps1 -BackupPath <path> -ConfirmRestore`.
- Set `ADMIN_METRICS_TOKEN` to enable the private `/metrics` view with queue,
  per-tool status, retry, queue-wait, and execution-time statistics.

Long provider tools write private atomic checkpoints per bounded document part.
If their worker is interrupted, the dispatcher reconciles a complete result or
requeues the same job up to `MAX_JOB_ATTEMPTS` without repeating saved provider
steps. Search and fast entity extraction have their own queue, so a long
translation cannot block them.

## Verification

- `docker compose --profile test run --rm test` runs compile, unit, and contract checks.
- `powershell -File scripts/run_acceptance.ps1` runs the two-round ten-workspace load.
- `python scripts/live_tool_acceptance.py` from the Compose network exercises all seven tools and their downloads.
- `node tests/e2e/browser_smoke.js` checks all tabs at 1440, 768, 390, and 375 pixels when Playwright is available.

## OpenRouter configuration

The generation boundary is `openrouter_client.py`. It reads these variable names:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (default `qwen/qwen3-30b-a3b-instruct-2507`)
- `OPENROUTER_TIMEOUT_SECONDS`, `OPENROUTER_MAX_TOKENS`, `OPENROUTER_TEMPERATURE`
- `OPENROUTER_MAX_RETRIES`, `OPENROUTER_HTTP_REFERER`, `OPENROUTER_APP_TITLE`

The client uses bounded retries for transient failures only. It never logs API
keys or complete document prompts and rejects empty/error/refusal-style output
before it reaches the interface or a download.

## RAG document scope

After indexing, choose an active document in the sidebar. RAG retrieval uses an
exact OpenSearch `metadata.source.keyword` filter for that document. Select
`كل المستندات` to search the full corpus explicitly. Cache identity includes the
question, recent message contents, active document, model, and index.

## Notes

- The durable API accepts PDF files up to 25 MB and 100 pages. Direct text,
  scanned pages, and mixed PDFs preserve their original page numbering; sparse
  image pages use Arabic/English OCR automatically.
- Do not delete or rebuild OpenSearch volumes/indexes to migrate the generation
  provider; vector dimensions and indexed data are intentionally untouched.
- SearXNG web results stay separate from normal RAG context and are only sent to
  OpenRouter when the user explicitly asks to summarize search results.
