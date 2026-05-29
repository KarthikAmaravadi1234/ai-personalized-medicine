"""Tie the embedder, chunker, and vector store together for indexing and retrieval."""

from __future__ import annotations

import re
from pathlib import Path

from backend.rag.chunker import chunk_text
from backend.rag.embedder import Embedder, get_embedder
from backend.rag.store import SearchHit, VectorStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_DIR = _PROJECT_ROOT / "data" / "knowledge"
DEFAULT_INDEX_PATH = _PROJECT_ROOT / "data" / "knowledge_index.json"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    """Remove a leading YAML frontmatter block so provenance metadata isn't embedded."""
    return _FRONTMATTER_RE.sub("", text, count=1)


class Retriever:
    def __init__(self, embedder: Embedder | None = None, store: VectorStore | None = None) -> None:
        self.embedder = embedder or get_embedder()
        self.store = store or VectorStore()

    def index_directory(
        self,
        directory: str | Path = DEFAULT_KNOWLEDGE_DIR,
        *,
        pattern: str = "*.md",
    ) -> int:
        """Chunk and embed every matching file in ``directory``. Returns chunk count."""
        directory = Path(directory)
        self.store.clear()

        texts: list[str] = []
        sources: list[str] = []
        indices: list[int] = []
        for file in sorted(directory.glob(pattern)):
            content = _strip_frontmatter(file.read_text())
            for chunk in chunk_text(content, source=file.name):
                texts.append(chunk.text)
                sources.append(chunk.source)
                indices.append(chunk.chunk_index)

        if texts:
            embeddings = self.embedder.embed(texts)
            self.store.add(texts, sources, indices, embeddings)
        return len(texts)

    def search(self, query: str, top_k: int = 4) -> list[SearchHit]:
        if len(self.store) == 0:
            return []
        query_embedding = self.embedder.embed([query])[0]
        return self.store.search(query_embedding, top_k=top_k)

    def save(self, path: str | Path = DEFAULT_INDEX_PATH) -> None:
        self.store.save(path)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_INDEX_PATH, embedder: Embedder | None = None) -> "Retriever":
        return cls(embedder=embedder, store=VectorStore.load(path))
