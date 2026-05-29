"""Render a patient's structured records into short text documents for embedding.

These documents are embedded per-patient at chat time and searched semantically so
the agent can surface the facts most relevant to a free-form question. They are never
persisted into the shared knowledge index, which keeps patient data scoped per patient.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.agents.tools import LabReading, bmi_category
from backend.models.orm import Patient, Vital

if TYPE_CHECKING:
    from backend.ml.predict import RiskPrediction

# A (text, source) pair: the text is embedded, the source labels its origin.
PatientDoc = tuple[str, str]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG_RE.sub("_", text.lower()).strip("_") or "item"


def _reference_phrase(lab: LabReading) -> str:
    if lab.reference_low is not None and lab.reference_high is not None:
        return f"reference {lab.reference_low}-{lab.reference_high}"
    if lab.reference_high is not None:
        return f"reference up to {lab.reference_high}"
    if lab.reference_low is not None:
        return f"reference from {lab.reference_low}"
    return "no reference range"


def build_patient_documents(
    patient: Patient,
    labs: list[LabReading],
    vitals: list[Vital],
    bmi: float | None,
    risk: "RiskPrediction | None",
) -> list[PatientDoc]:
    """Build short, factual documents describing a single patient's records."""
    docs: list[PatientDoc] = []

    sex = getattr(patient.sex, "value", patient.sex) or "unknown"
    demo_bits = [f"{patient.age}-year-old" if patient.age is not None else "age unknown", str(sex)]
    if patient.height_cm:
        demo_bits.append(f"height {patient.height_cm}cm")
    if patient.weight_kg:
        demo_bits.append(f"weight {patient.weight_kg}kg")
    if bmi is not None:
        demo_bits.append(f"BMI {bmi} ({bmi_category(bmi)})")
    name = patient.name or f"patient {patient.id}"
    docs.append((f"Demographics for {name}: " + ", ".join(demo_bits) + ".", "patient:demographics"))

    for lab in labs:
        unit = lab.unit or ""
        docs.append(
            (
                f"Lab {lab.test_name} = {lab.value}{unit} ({lab.flag}; {_reference_phrase(lab)}).",
                f"patient:lab:{_slug(lab.test_name)}",
            )
        )

    for v in vitals:
        when = v.recorded_at.isoformat() if v.recorded_at else "undated"
        bits: list[str] = []
        if v.systolic_bp and v.diastolic_bp:
            bits.append(f"BP {v.systolic_bp}/{v.diastolic_bp} mmHg")
        if v.heart_rate:
            bits.append(f"HR {v.heart_rate} bpm")
        if v.steps is not None:
            bits.append(f"steps {v.steps}")
        if v.sleep_hours is not None:
            bits.append(f"sleep {v.sleep_hours}h")
        if bits:
            docs.append((f"Vitals {when}: " + ", ".join(bits) + ".", f"patient:vitals:{when}"))

    if risk is not None:
        drivers = ", ".join(c.feature for c in risk.contributions[:3])
        docs.append(
            (
                f"Type 2 diabetes risk: {risk.risk_level} (p={risk.probability}); "
                f"top drivers: {drivers}.",
                "patient:risk",
            )
        )

    return docs
