"""In-memory vector store with cosine similarity search and JSON persistence.

Kept intentionally simple and dependency-free. The interface (add / search / save /
load) mirrors what a real vector database provides, so ChromaDB or pgvector can be
swapped in later without changing callers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class StoredChunk:
    text: str
    source: str
    chunk_index: int
    embedding: list[float]


@dataclass
class SearchHit:
    text: str
    source: str
    chunk_index: int
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    # Vectors are stored L2-normalized, so the dot product is the cosine similarity.
    return sum(x * y for x, y in zip(a, b))


class VectorStore:
    def __init__(self) -> None:
        self._chunks: list[StoredChunk] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()

    def add(
        self,
        texts: list[str],
        sources: list[str],
        chunk_indices: list[int],
        embeddings: list[list[float]],
    ) -> None:
        for text, source, idx, emb in zip(texts, sources, chunk_indices, embeddings):
            self._chunks.append(
                StoredChunk(text=text, source=source, chunk_index=idx, embedding=emb)
            )

    def search(self, query_embedding: list[float], top_k: int = 4) -> list[SearchHit]:
        scored = [
            SearchHit(
                text=c.text,
                source=c.source,
                chunk_index=c.chunk_index,
                score=_cosine(query_embedding, c.embedding),
            )
            for c in self._chunks
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(c) for c in self._chunks]
        path.write_text(json.dumps(payload))

    @classmethod
    def load(cls, path: str | Path) -> "VectorStore":
        store = cls()
        data = json.loads(Path(path).read_text())
        store._chunks = [StoredChunk(**item) for item in data]
        return store
