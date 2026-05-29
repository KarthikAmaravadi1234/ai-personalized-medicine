"""Assemble cited answers from retrieved chunks.

The default behavior is extractive: it returns the most relevant passages plus their
source citations, with no external LLM call. This keeps the pipeline runnable offline
and makes citations verifiable. An LLM synthesis step can be layered on later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.rag.retriever import Retriever
from backend.rag.store import SearchHit


@dataclass
class Citation:
    source: str
    chunk_index: int
    excerpt: str
    score: float


@dataclass
class Answer:
    query: str
    answer: str
    citations: list[Citation]


def _excerpt(text: str, max_chars: int = 240) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "\u2026"


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _best_excerpt(text: str, query: str, retriever: Retriever) -> str:
    """Pick the sentence most relevant to ``query`` so the answer is crisp."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    if len(sentences) <= 1:
        return _excerpt(text)
    try:
        vectors = retriever.embedder.embed([*sentences, query])
        query_vec = vectors[-1]
        best = max(
            range(len(sentences)),
            key=lambda i: sum(a * b for a, b in zip(vectors[i], query_vec)),
        )
        return _excerpt(sentences[best])
    except Exception:  # noqa: BLE001 - never let excerpt selection fail a response
        return _excerpt(text)


def answer_question(
    query: str,
    retriever: Retriever,
    *,
    top_k: int = 3,
    min_score: float = 0.01,
) -> Answer:
    hits: list[SearchHit] = retriever.search(query, top_k=top_k)
    hits = [h for h in hits if h.score >= min_score]

    if not hits:
        return Answer(
            query=query,
            answer=(
                "I couldn't find anything relevant in the knowledge base. "
                "Try rephrasing, or add more source documents."
            ),
            citations=[],
        )

    citations = [
        Citation(
            source=h.source,
            chunk_index=h.chunk_index,
            excerpt=_best_excerpt(h.text, query, retriever),
            score=round(h.score, 4),
        )
        for h in hits
    ]
    summary = " ".join(c.excerpt for c in citations)
    answer_text = (
        f"Based on the knowledge base ({', '.join(sorted({c.source for c in citations}))}): "
        f"{summary}"
    )
    return Answer(query=query, answer=answer_text, citations=citations)
