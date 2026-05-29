"""Tools the health agent can call.

Each tool is a small, testable function over the existing data and RAG layers. The
agent records which tools it invoked so responses are auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.orm import LabResult, Patient, Vital
from backend.rag.retriever import Retriever
from backend.rag.store import SearchHit

if TYPE_CHECKING:
    from backend.ml.predict import RiskPrediction


@dataclass
class ToolCall:
    tool: str
    args: dict
    summary: str


@dataclass
class LabReading:
    test_name: str
    value: float
    unit: str | None
    reference_low: float | None
    reference_high: float | None

    @property
    def flag(self) -> str:
        """Classify the reading against its reference range."""
        if self.reference_low is not None and self.value < self.reference_low:
            return "low"
        if self.reference_high is not None and self.value > self.reference_high:
            return "high"
        return "normal"


def get_patient(db: Session, patient_id: int) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_labs(db: Session, patient_id: int) -> list[LabReading]:
    stmt = select(LabResult).where(LabResult.patient_id == patient_id).order_by(LabResult.test_name)
    return [
        LabReading(
            test_name=row.test_name,
            value=row.value,
            unit=row.unit,
            reference_low=row.reference_low,
            reference_high=row.reference_high,
        )
        for row in db.scalars(stmt)
    ]


def get_patient_vitals(db: Session, patient_id: int) -> list[Vital]:
    stmt = select(Vital).where(Vital.patient_id == patient_id).order_by(Vital.id)
    return list(db.scalars(stmt))


def calculate_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    meters = height_cm / 100.0
    return round(weight_kg / (meters * meters), 1)


def bmi_category(bmi: float | None) -> str | None:
    if bmi is None:
        return None
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal weight"
    if bmi < 30:
        return "overweight"
    return "obese"


def search_knowledge(retriever: Retriever, query: str, top_k: int = 3) -> list[SearchHit]:
    return retriever.search(query, top_k=top_k)


@dataclass
class GatheredContext:
    """Everything the agent collected for a turn, plus the audit log of tool calls."""

    patient: Patient
    labs: list[LabReading] = field(default_factory=list)
    vitals: list[Vital] = field(default_factory=list)
    bmi: float | None = None
    knowledge_hits: list[SearchHit] = field(default_factory=list)
    risk: "RiskPrediction | None" = None
    tool_calls: list[ToolCall] = field(default_factory=list)
