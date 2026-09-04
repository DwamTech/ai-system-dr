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

The default runtime contains `streamlit-app`, `opensearch`, `redis`, and
`searxng`. Their host ports are bound to `127.0.0.1`; Streamlit is likewise
local-only by default. For a shared deployment, add an authenticated reverse
proxy and TLS rather than exposing internal services directly.

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

- Streamlit upload configuration remains `8192` MB per file. PDF validation
  checks extension and the PDF signature without introducing a smaller limit.
- Do not delete or rebuild OpenSearch volumes/indexes to migrate the generation
  provider; vector dimensions and indexed data are intentionally untouched.
- SearXNG web results stay separate from normal RAG context and are only sent to
  OpenRouter when the user explicitly asks to summarize search results.
