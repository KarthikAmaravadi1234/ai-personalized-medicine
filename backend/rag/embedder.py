"""Embedding backends for the RAG pipeline.

The default :class:`LocalHashEmbedder` is dependency-free and deterministic, so the
pipeline runs and is testable offline. :class:`OpenAIEmbedder` is an optional drop-in
that uses real embeddings when an API key and the ``openai`` package are available.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

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

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        # Optional per-bucket inverse-document-frequency weights, set by ``fit``.
        self._idf: list[float] | None = None

    def _bucket(self, token: str) -> int:
        # Use a stable hash (not Python's salted ``hash()``) so embeddings are
        # identical across processes; otherwise stored vectors and later query
        # vectors would land in different buckets and retrieval would be unreliable.
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def fit(self, corpus: list[str]) -> "LocalHashEmbedder":
        """Learn IDF weights so corpus-wide common words are down-weighted.

        Without this, raw term frequency lets generic words dominate similarity on a
        broad corpus; IDF lets topic-specific terms (e.g. "hba1c") drive retrieval.
        """
        n = len(corpus)
        if n == 0:
            self._idf = None
            return self
        doc_freq = [0] * self.dim
        for text in corpus:
            seen: set[int] = set()
            for token in tokenize(text):
                bucket = self._bucket(token)
                if bucket not in seen:
                    doc_freq[bucket] += 1
                    seen.add(bucket)
        self._idf = [math.log((1 + n) / (1 + df)) + 1.0 for df in doc_freq]
        return self

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            vector[self._bucket(token)] += 1.0
        if self._idf is not None:
            vector = [v * self._idf[i] for i, v in enumerate(vector)]
        return _l2_normalize(vector)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class OpenAIEmbedder:
    """OpenAI embeddings backend (optional; requires ``openai`` and an API key)."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        from openai import OpenAI  # imported lazily so the package stays optional

        self.model = model
        # Fail fast (one retry) so a quota/auth error degrades to local quickly.
        self._client = OpenAI(api_key=api_key, max_retries=1) if api_key else OpenAI(max_retries=1)
        # Dimensions for text-embedding-3-small; overridden after first call if needed.
        self.dim = 1536

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.model, input=texts)
        vectors = [item.embedding for item in response.data]
        if vectors:
            self.dim = len(vectors[0])
        return vectors


class ResilientEmbedder:
    """Wraps a primary embedder and permanently fails over to a fallback on any error.

    Once it switches to the fallback it stays there, so all docs and queries are
    embedded by the same backend (consistent vector space within an index).
    """

    def __init__(self, primary: Embedder, fallback: Embedder) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active = primary
        self.dim = primary.dim

    def fit(self, corpus: list[str]) -> "ResilientEmbedder":
        # Only IDF-style backends implement ``fit``; OpenAI embeddings ignore it.
        for emb in (self._primary, self._fallback):
            fit = getattr(emb, "fit", None)
            if callable(fit):
                fit(corpus)
        return self

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._active is self._primary:
            try:
                vectors = self._primary.embed(texts)
                self.dim = self._primary.dim
                return vectors
            except Exception as exc:  # noqa: BLE001 - any failure -> offline fallback
                from backend.llm import get_circuit, is_quota_or_auth_error

                if is_quota_or_auth_error(exc):
                    get_circuit().trip(str(exc))
                logger.warning("Embedding backend failed, falling back to local: %s", exc)
                self._active = self._fallback
        self.dim = self._fallback.dim
        return self._fallback.embed(texts)


def get_embedder() -> Embedder:
    """Return the best available embedder.

    Uses OpenAI when ``OPENAI_API_KEY`` is set and the package is importable, wrapped
    so any runtime failure (quota, network) falls back to the local deterministic
    embedder; otherwise uses the local embedder directly.
    """
    from backend.config import get_settings
    from backend.llm import get_circuit

    settings = get_settings()
    # Skip OpenAI while the circuit is tripped (recent quota/auth failure).
    if settings.openai_api_key and get_circuit().is_available():
        try:
            primary = OpenAIEmbedder(
                model=settings.openai_embedding_model, api_key=settings.openai_api_key
            )
            return ResilientEmbedder(primary=primary, fallback=LocalHashEmbedder())
        except Exception:
            pass
    return LocalHashEmbedder()
