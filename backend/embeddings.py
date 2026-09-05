"""A bounded client for the single embeddings service."""

from __future__ import annotations

import os
from typing import Sequence

import requests


class RemoteEmbeddings:
    """Minimal LangChain embeddings interface backed by the shared model service."""

    def __init__(self, endpoint: str | None = None, batch_size: int | None = None):
        self.endpoint = (endpoint or os.getenv("EMBEDDINGS_URL", "")).rstrip("/")
        self.batch_size = batch_size or int(os.getenv("EMBEDDINGS_BATCH_SIZE", "32"))
        self.timeout = float(os.getenv("EMBEDDINGS_TIMEOUT_SECONDS", "45"))
        if not self.endpoint:
            raise RuntimeError("EMBEDDINGS_URL is required for RemoteEmbeddings")

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start:start + self.batch_size])
            response = requests.post(
                f"{self.endpoint}/embeddings",
                json={"texts": batch},
                timeout=(3, self.timeout),
            )
            response.raise_for_status()
            payload = response.json()
            vectors = payload.get("vectors")
            if not isinstance(vectors, list) or len(vectors) != len(batch):
                raise RuntimeError("Embedding service returned an invalid batch")
            embeddings.extend(vectors)
        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]
