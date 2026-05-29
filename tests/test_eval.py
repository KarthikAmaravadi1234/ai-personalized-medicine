from backend.rag.embedder import LocalHashEmbedder
from backend.rag.eval.run_eval import evaluate
from backend.rag.retriever import Retriever
from backend.rag.store import VectorStore


def test_retrieval_recall_meets_threshold() -> None:
    retriever = Retriever(embedder=LocalHashEmbedder(dim=512), store=VectorStore())
    retriever.index_directory()
    report = evaluate(retriever, top_k=3)
    # All golden queries should retrieve their expected source within top-3.
    assert report.recall_at_k >= 0.8, [
        (r.query, r.retrieved_sources) for r in report.results if not r.hit
    ]
