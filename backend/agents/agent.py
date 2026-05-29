"""The health agent.

``RuleBasedAgent`` is the default: it performs real tool-calling over the patient's
data and the knowledge base, with no LLM, so it runs and tests offline. ``get_agent``
exposes a seam to swap in an LLM-backed agent (e.g. LangGraph + OpenAI) later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.agents import tools
from backend.agents.guardrails import apply_guardrails
from backend.agents.tools import GatheredContext, ToolCall, bmi_category
from backend.rag.retriever import Retriever
from backend.rag.store import SearchHit


class PatientNotFoundError(Exception):
    """Raised when the requested patient does not exist."""


@dataclass
class Citation:
    source: str
    chunk_index: int
    excerpt: str
    score: float


@dataclass
class AgentResponse:
    patient_id: int
    answer: str
    citations: list[Citation] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    guardrail_notes: list[str] = field(default_factory=list)


# Keyword -> knowledge query hints, used to decide when to consult the knowledge base.
_TOPIC_HINTS = {
    "ldl": "LDL cholesterol",
    "hdl": "HDL cholesterol",
    "cholesterol": "cholesterol",
    "triglyceride": "triglycerides",
    "glucose": "fasting glucose diabetes",
    "sugar": "fasting glucose diabetes",
    "a1c": "HbA1c diabetes",
    "hba1c": "HbA1c diabetes",
    "diabet": "type 2 diabetes",
    "blood pressure": "high blood pressure hypertension",
    "hypertens": "high blood pressure hypertension",
    "bmi": "body mass index weight",
    "weight": "body mass index weight",
}


class RuleBasedAgent:
    def __init__(self, db: Session, retriever: Retriever) -> None:
        self.db = db
        self.retriever = retriever

    def _gather(self, patient_id: int, message: str) -> GatheredContext:
        patient = tools.get_patient(self.db, patient_id)
        if patient is None:
            raise PatientNotFoundError(f"Patient {patient_id} not found")

        ctx = GatheredContext(patient=patient)
        lowered = message.lower()

        wants_labs = any(w in lowered for w in ("lab", "ldl", "hdl", "cholesterol", "glucose", "a1c", "hba1c", "triglyceride"))
        wants_vitals = any(w in lowered for w in ("vital", "blood pressure", "heart rate", "pulse", "sleep", "steps"))
        wants_bmi = any(w in lowered for w in ("bmi", "weight", "body mass"))
        wants_risk = any(w in lowered for w in ("risk", "diabet", "chance", "likelihood", "likely"))
        # Default to showing labs when the question is generic ("how am I doing?").
        if not (wants_labs or wants_vitals or wants_bmi or wants_risk):
            wants_labs = True

        if wants_labs:
            ctx.labs = tools.get_patient_labs(self.db, patient_id)
            ctx.tool_calls.append(
                ToolCall("get_patient_labs", {"patient_id": patient_id}, f"{len(ctx.labs)} lab results")
            )
        if wants_vitals:
            ctx.vitals = tools.get_patient_vitals(self.db, patient_id)
            ctx.tool_calls.append(
                ToolCall("get_patient_vitals", {"patient_id": patient_id}, f"{len(ctx.vitals)} vital records")
            )
        if wants_bmi:
            ctx.bmi = tools.calculate_bmi(patient.height_cm, patient.weight_kg)
            ctx.tool_calls.append(
                ToolCall(
                    "calculate_bmi",
                    {"height_cm": patient.height_cm, "weight_kg": patient.weight_kg},
                    f"BMI={ctx.bmi}",
                )
            )

        if wants_risk:
            # Lazy import avoids a circular import (ml.features imports agent tools).
            from backend.ml.predict import score_patient

            _, prediction = score_patient(self.db, patient)
            ctx.risk = prediction
            ctx.tool_calls.append(
                ToolCall(
                    "get_risk_score",
                    {"patient_id": patient_id, "condition": "type_2_diabetes"},
                    f"{prediction.risk_level} ({prediction.probability})",
                )
            )

        query = self._knowledge_query(lowered, ctx, wants_risk=wants_risk)
        if query:
            ctx.knowledge_hits = tools.search_knowledge(self.retriever, query, top_k=3)
            ctx.tool_calls.append(
                ToolCall("search_knowledge", {"query": query}, f"{len(ctx.knowledge_hits)} hits")
            )
        return ctx

    @staticmethod
    def _knowledge_query(lowered: str, ctx: GatheredContext, *, wants_risk: bool = False) -> str:
        hints = [hint for key, hint in _TOPIC_HINTS.items() if key in lowered]
        if wants_risk:
            hints.append("type 2 diabetes")
        if hints:
            return "; ".join(dict.fromkeys(hints))
        # Fall back to topics implied by abnormal labs so answers stay grounded.
        abnormal = [lab.test_name for lab in ctx.labs if lab.flag != "normal"]
        return "; ".join(abnormal) if abnormal else ""

    def _compose(self, ctx: GatheredContext, message: str) -> tuple[str, list[Citation]]:
        parts: list[str] = []
        name = ctx.patient.name or f"patient {ctx.patient.id}"
        parts.append(f"Here is what your data shows, {name}:")

        if ctx.labs:
            abnormal = [lab for lab in ctx.labs if lab.flag != "normal"]
            if abnormal:
                summarized = ", ".join(
                    f"{lab.test_name} {lab.value}{lab.unit or ''} ({lab.flag})" for lab in abnormal
                )
                parts.append(f"Labs outside the typical range: {summarized}.")
            else:
                parts.append("Your recorded labs are within typical reference ranges.")

        if ctx.vitals:
            v = ctx.vitals[-1]
            vital_bits = []
            if v.systolic_bp and v.diastolic_bp:
                vital_bits.append(f"blood pressure {v.systolic_bp}/{v.diastolic_bp} mmHg")
            if v.heart_rate:
                vital_bits.append(f"heart rate {v.heart_rate} bpm")
            if v.sleep_hours is not None:
                vital_bits.append(f"sleep {v.sleep_hours} h")
            if vital_bits:
                parts.append("Recent vitals: " + ", ".join(vital_bits) + ".")

        if ctx.bmi is not None:
            parts.append(f"Your BMI is approximately {ctx.bmi} ({bmi_category(ctx.bmi)}).")

        if ctx.risk is not None:
            top = ctx.risk.contributions[:2]
            drivers = ", ".join(c.feature for c in top)
            pct = round(ctx.risk.probability * 100)
            parts.append(
                f"A baseline model estimates your type 2 diabetes risk as {ctx.risk.risk_level} "
                f"(about {pct}%), driven mainly by {drivers}. This is a statistical estimate "
                f"from an educational model, not a diagnosis."
            )

        citations: list[Citation] = []
        if ctx.knowledge_hits:
            citations = [_to_citation(h) for h in ctx.knowledge_hits]
            sources = ", ".join(sorted({c.source for c in citations}))
            top = ctx.knowledge_hits[0]
            parts.append(
                f"From the knowledge base ({sources}): {_excerpt(top.text)}"
            )

        return " ".join(parts), citations

    def chat(self, patient_id: int, message: str) -> AgentResponse:
        ctx = self._gather(patient_id, message)
        answer, citations = self._compose(ctx, message)
        guarded = apply_guardrails(answer, has_citations=bool(citations))
        return AgentResponse(
            patient_id=patient_id,
            answer=guarded.text,
            citations=citations,
            tool_calls=ctx.tool_calls,
            guardrail_notes=guarded.notes,
        )


def _to_citation(hit: SearchHit) -> Citation:
    return Citation(
        source=hit.source,
        chunk_index=hit.chunk_index,
        excerpt=_excerpt(hit.text),
        score=round(hit.score, 4),
    )


def _excerpt(text: str, max_chars: int = 240) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "\u2026"


def get_agent(db: Session, retriever: Retriever) -> RuleBasedAgent:
    """Return the configured agent.

    Currently always the offline rule-based agent. When an LLM backend is added,
    select it here based on ``settings.openai_api_key`` and package availability.
    """
    return RuleBasedAgent(db=db, retriever=retriever)
