from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.agent import PatientNotFoundError, get_agent
from backend.api.routes.knowledge import get_retriever
from backend.db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    patient_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1)


class CitationOut(BaseModel):
    source: str
    chunk_index: int
    excerpt: str
    score: float


class ToolCallOut(BaseModel):
    tool: str
    args: dict
    summary: str


class ChatResponse(BaseModel):
    patient_id: int
    answer: str
    citations: list[CitationOut]
    tool_calls: list[ToolCallOut]
    guardrail_notes: list[str]


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    agent = get_agent(db=db, retriever=get_retriever())
    try:
        result = agent.chat(payload.patient_id, payload.message)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ChatResponse(
        patient_id=result.patient_id,
        answer=result.answer,
        citations=[CitationOut(**vars(c)) for c in result.citations],
        tool_calls=[ToolCallOut(**vars(t)) for t in result.tool_calls],
        guardrail_notes=result.guardrail_notes,
    )
