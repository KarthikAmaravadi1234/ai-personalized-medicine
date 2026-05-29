"""Split documents into overlapping word-based chunks for retrieval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int


def chunk_text(
    text: str,
    source: str,
    *,
    chunk_size: int = 120,
    overlap: int = 20,
) -> list[Chunk]:
    """Split ``text`` into chunks of roughly ``chunk_size`` words.

    Chunks overlap by ``overlap`` words so that information spanning a boundary is
    still retrievable. ``source`` identifies the originating document.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    for index, start in enumerate(range(0, len(words), step)):
        window = words[start : start + chunk_size]
        if not window:
            break
        chunks.append(Chunk(text=" ".join(window), source=source, chunk_index=index))
        if start + chunk_size >= len(words):
            break
    return chunks
