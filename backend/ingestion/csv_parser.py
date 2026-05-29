"""Parse uploaded patient CSV files into validated Pydantic models.

Expected columns (matching scripts/generate_synthetic_patients.py output):

    external_id, name, sex, age, height_cm, weight_kg,
    <lab columns...>, heart_rate, systolic_bp, diastolic_bp, steps, sleep_hours

Lab columns are any header listed in ``LAB_COLUMN_SPECS``; each non-empty cell
becomes a LabResult. Vital columns become a single Vital record per row.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
import sys
from pathlib import Path

from pydantic import ValidationError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.models.schemas import LabResultCreate, PatientCreate, VitalCreate

# Lab header -> (unit, reference_low, reference_high)
LAB_COLUMN_SPECS: dict[str, tuple[str, float | None, float | None]] = {
    "LDL Cholesterol": ("mg/dL", None, 100),
    "HDL Cholesterol": ("mg/dL", 40, None),
    "Total Cholesterol": ("mg/dL", None, 200),
    "Triglycerides": ("mg/dL", None, 150),
    "Fasting Glucose": ("mg/dL", 70, 99),
    "HbA1c": ("%", 4.0, 5.6),
}

DEMOGRAPHIC_COLUMNS = {"external_id", "name", "sex", "age", "height_cm", "weight_kg"}
VITAL_COLUMNS = {"heart_rate", "systolic_bp", "diastolic_bp", "steps", "sleep_hours"}


@dataclass
class ParseResult:
    patients: list[PatientCreate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _to_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    return None if cleaned is None else float(cleaned)


def _to_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    return None if cleaned is None else int(float(cleaned))


def _build_labs(row: dict[str, str]) -> list[LabResultCreate]:
    labs: list[LabResultCreate] = []
    for column, (unit, ref_low, ref_high) in LAB_COLUMN_SPECS.items():
        if column not in row:
            continue
        value = _to_float(row.get(column))
        if value is None:
            continue
        labs.append(
            LabResultCreate(
                test_name=column,
                value=value,
                unit=unit,
                reference_low=ref_low,
                reference_high=ref_high,
            )
        )
    return labs


def _build_vitals(row: dict[str, str]) -> list[VitalCreate]:
    fields = {
        "heart_rate": _to_int(row.get("heart_rate")),
        "systolic_bp": _to_int(row.get("systolic_bp")),
        "diastolic_bp": _to_int(row.get("diastolic_bp")),
        "steps": _to_int(row.get("steps")),
        "sleep_hours": _to_float(row.get("sleep_hours")),
    }
    if all(v is None for v in fields.values()):
        return []
    return [VitalCreate(**fields)]


def parse_patients_csv(content: str | bytes) -> ParseResult:
    """Parse CSV text/bytes into PatientCreate models, collecting per-row errors."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    result = ParseResult()
    reader = csv.DictReader(io.StringIO(content))

    if reader.fieldnames is None:
        result.errors.append("CSV is empty or has no header row.")
        return result

    for line_no, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            patient = PatientCreate(
                external_id=_clean(row.get("external_id")),
                name=_clean(row.get("name")),
                sex=_clean(row.get("sex")) or "unknown",
                age=_to_int(row.get("age")),
                height_cm=_to_float(row.get("height_cm")),
                weight_kg=_to_float(row.get("weight_kg")),
                labs=_build_labs(row),
                vitals=_build_vitals(row),
            )
            result.patients.append(patient)
        except (ValidationError, ValueError) as exc:
            result.errors.append(f"Row {line_no}: {exc}")

    return result
