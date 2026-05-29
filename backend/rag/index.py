"""CLI to build the knowledge vector index from data/knowledge/.

Usage:
    python backend/rag/index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.rag.retriever import DEFAULT_INDEX_PATH, DEFAULT_KNOWLEDGE_DIR, Retriever


def build_index() -> int:
    retriever = Retriever()
    count = retriever.index_directory(DEFAULT_KNOWLEDGE_DIR)
    retriever.save(DEFAULT_INDEX_PATH)
    return count


if __name__ == "__main__":
    n = build_index()
    print(f"Indexed {n} chunks from {DEFAULT_KNOWLEDGE_DIR}")
    print(f"Index written to {DEFAULT_INDEX_PATH}")
