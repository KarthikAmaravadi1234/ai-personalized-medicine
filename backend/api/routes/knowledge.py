from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.rag.qa import answer_question
from backend.rag.retriever import Retriever

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Return a process-wide retriever, indexing the knowledge dir on first use."""
    global _retriever
    if _retriever is None:
        retriever = Retriever()
        retriever.index_directory()
        _retriever = retriever
    return _retriever


class SearchHitOut(BaseModel):
    source: str
    chunk_index: int
    score: float
    text: str


class CitationOut(BaseModel):
    source: str
    chunk_index: int
    excerpt: str
    score: float


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationOut]


class ReindexResponse(BaseModel):
    indexed_chunks: int


@router.get("/search", response_model=list[SearchHitOut])
def search_knowledge(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(4, ge=1, le=20),
) -> list[SearchHitOut]:
    hits = get_retriever().search(q, top_k=top_k)
    return [
        SearchHitOut(
            source=h.source, chunk_index=h.chunk_index, score=round(h.score, 4), text=h.text
        )
        for h in hits
    ]


@router.get("/ask", response_model=AskResponse)
def ask_knowledge(
    q: str = Query(..., min_length=1, description="Question"),
    top_k: int = Query(3, ge=1, le=10),
) -> AskResponse:
    result = answer_question(q, get_retriever(), top_k=top_k)
    return AskResponse(
        query=result.query,
        answer=result.answer,
        citations=[CitationOut(**vars(c)) for c in result.citations],
    )


@router.post("/reindex", response_model=ReindexResponse)
def reindex_knowledge() -> ReindexResponse:
    retriever = get_retriever()
    count = retriever.index_directory()
    return ReindexResponse(indexed_chunks=count)
