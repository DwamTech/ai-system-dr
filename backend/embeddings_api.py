"""Single-process embeddings service shared by indexing and chat workers."""

from __future__ import annotations

import os
import threading
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer


MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
MAX_BATCH = int(os.getenv("EMBEDDINGS_MAX_BATCH", "32"))
MAX_TEXT_CHARS = int(os.getenv("EMBEDDINGS_MAX_TEXT_CHARS", "16000"))
_model_lock = threading.BoundedSemaphore(int(os.getenv("EMBEDDINGS_CONCURRENCY", "1")))

app = FastAPI(title="AI Conference embeddings", docs_url=None, redoc_url=None)


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=MAX_BATCH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL_NAME, "loaded": bool(get_model.cache_info().currsize)}


@app.get("/ready")
def ready() -> dict:
    """Readiness is distinct from liveness: do not admit indexing before warmup."""
    try:
        get_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Embedding model is not ready") from exc
    return {"status": "ready", "model": MODEL_NAME}


@app.post("/embeddings")
def embeddings(request: EmbeddingRequest) -> dict:
    if any(not text.strip() or len(text) > MAX_TEXT_CHARS for text in request.texts):
        raise HTTPException(status_code=422, detail="Invalid embedding input")
    # The model is CPU-bound. A bounded gate prevents parallel callers from
    # consuming all cores and stalling chat/status traffic.
    with _model_lock:
        vectors = get_model().encode(
            request.texts,
            batch_size=min(MAX_BATCH, len(request.texts)),
            normalize_embeddings=False,
            show_progress_bar=False,
        ).tolist()
    return {"vectors": vectors, "model": MODEL_NAME}
