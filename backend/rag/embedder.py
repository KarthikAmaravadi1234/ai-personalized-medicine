"""Embedding backends for the RAG pipeline.

The default :class:`LocalHashEmbedder` is dependency-free and deterministic, so the
pipeline runs and is testable offline. :class:`OpenAIEmbedder` is an optional drop-in
that uses real embeddings when an API key and the ``openai`` package are available.
"""

from __future__ import annotations

import math
import re
from typing import Protocol, runtime_checkable

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


class LocalHashEmbedder:
    """Hashing-trick bag-of-words embedder with term-frequency weighting.

    Tokens are hashed into a fixed-dimension vector; counts are L2-normalized. This
    captures lexical overlap well enough for small corpora and keeps tests offline.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            bucket = hash((self.dim, token)) % self.dim
            vector[bucket] += 1.0
        return _l2_normalize(vector)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class OpenAIEmbedder:
    """OpenAI embeddings backend (optional; requires ``openai`` and an API key)."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        from openai import OpenAI  # imported lazily so the package stays optional

        self.model = model
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()
        # Dimensions for text-embedding-3-small; overridden after first call if needed.
        self.dim = 1536

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.model, input=texts)
        vectors = [item.embedding for item in response.data]
        if vectors:
            self.dim = len(vectors[0])
        return vectors


def get_embedder() -> Embedder:
    """Return the best available embedder.

    Uses OpenAI when ``OPENAI_API_KEY`` is set and the package is importable;
    otherwise falls back to the local deterministic embedder.
    """
    from backend.config import get_settings

    settings = get_settings()
    if settings.openai_api_key:
        try:
            return OpenAIEmbedder(api_key=settings.openai_api_key)
        except Exception:
            pass
    return LocalHashEmbedder()
