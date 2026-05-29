import pytest

from backend.rag.chunker import chunk_text
from backend.rag.embedder import LocalHashEmbedder
from backend.rag.qa import answer_question
from backend.rag.retriever import Retriever
from backend.rag.store import VectorStore


def test_chunker_overlap_and_coverage() -> None:
    text = " ".join(f"w{i}" for i in range(250))
    chunks = chunk_text(text, source="doc.md", chunk_size=100, overlap=20)
    assert len(chunks) >= 3
    assert chunks[0].source == "doc.md"
    assert chunks[0].chunk_index == 0
    # Overlap: last words of chunk 0 reappear at the start of chunk 1.
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-20:] == second_words[:20]


def test_chunker_empty_text() -> None:
    assert chunk_text("", source="x") == []


def test_chunker_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text("a b c", source="x", chunk_size=2, overlap=2)


def test_local_embedder_is_normalized_and_deterministic() -> None:
    emb = LocalHashEmbedder(dim=64)
    v1 = emb.embed(["elevated LDL cholesterol"])[0]
    v2 = emb.embed(["elevated LDL cholesterol"])[0]
    assert v1 == v2
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def _build_retriever() -> Retriever:
    retriever = Retriever(embedder=LocalHashEmbedder(dim=512), store=VectorStore())
    count = retriever.index_directory()
    assert count > 0
    return retriever


def test_retriever_finds_relevant_document() -> None:
    retriever = _build_retriever()
    hits = retriever.search("What does elevated LDL cholesterol mean?", top_k=3)
    assert hits
    assert hits[0].source == "ldl_cholesterol.md"


def test_retriever_hba1c_query() -> None:
    retriever = _build_retriever()
    hits = retriever.search("normal HbA1c percentage for diabetes", top_k=3)
    assert any(h.source == "hba1c.md" for h in hits)


def test_answer_question_returns_citations() -> None:
    retriever = _build_retriever()
    answer = answer_question("How can I lower my blood pressure?", retriever, top_k=3)
    assert answer.citations
    assert any("hypertension.md" == c.source for c in answer.citations)


def test_retriever_empty_store_returns_no_hits() -> None:
    retriever = Retriever(embedder=LocalHashEmbedder(dim=64), store=VectorStore())
    assert retriever.search("anything") == []
