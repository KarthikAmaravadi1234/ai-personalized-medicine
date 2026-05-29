"""Evaluate retrieval quality against a small set of golden Q&A pairs.

Computes recall@k: the fraction of queries whose expected source document appears in
the top-k retrieved chunks. Run as a script for a report, or import ``evaluate`` in
tests to assert a quality threshold.

Usage:
    python backend/rag/eval/run_eval.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.rag.retriever import Retriever

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_qa.json"


@dataclass
class QueryResult:
    query: str
    expected_sources: list[str]
    retrieved_sources: list[str]
    hit: bool


@dataclass
class EvalReport:
    results: list[QueryResult]
    top_k: int

    @property
    def recall_at_k(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.hit for r in self.results) / len(self.results)


def load_golden(path: Path = GOLDEN_PATH) -> list[dict]:
    return json.loads(path.read_text())


def evaluate(retriever: Retriever | None = None, *, top_k: int = 3) -> EvalReport:
    if retriever is None:
        retriever = Retriever()
        retriever.index_directory()

    results: list[QueryResult] = []
    for item in load_golden():
        hits = retriever.search(item["query"], top_k=top_k)
        retrieved = [h.source for h in hits]
        hit = any(src in retrieved for src in item["expected_sources"])
        results.append(
            QueryResult(
                query=item["query"],
                expected_sources=item["expected_sources"],
                retrieved_sources=retrieved,
                hit=hit,
            )
        )
    return EvalReport(results=results, top_k=top_k)


def main() -> None:
    report = evaluate()
    print(f"Retrieval eval (recall@{report.top_k}): {report.recall_at_k:.0%}\n")
    for r in report.results:
        status = "PASS" if r.hit else "FAIL"
        print(f"[{status}] {r.query}")
        print(f"        expected={r.expected_sources} retrieved={r.retrieved_sources}")


if __name__ == "__main__":
    main()
