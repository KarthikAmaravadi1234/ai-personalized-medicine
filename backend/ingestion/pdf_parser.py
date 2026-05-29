"""Parse lab values out of PDF lab reports.

Text extraction (``pdfplumber``) is separated from parsing so the parsing logic is
fully testable offline without a real PDF. Recognized tests and their reference
ranges/units are shared with the CSV parser via ``LAB_COLUMN_SPECS``.
"""

from __future__ import annotations

import re

from backend.ingestion.csv_parser import LAB_COLUMN_SPECS
from backend.models.schemas import LabResultCreate, PatientCreate

# Aliases mapping free-text names found in reports to canonical test names.
_NAME_ALIASES: dict[str, str] = {
    "ldl": "LDL Cholesterol",
    "ldl cholesterol": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "hdl cholesterol": "HDL Cholesterol",
    "total cholesterol": "Total Cholesterol",
    "cholesterol total": "Total Cholesterol",
    "triglycerides": "Triglycerides",
    "trig": "Triglycerides",
    "fasting glucose": "Fasting Glucose",
    "glucose": "Fasting Glucose",
    "glucose fasting": "Fasting Glucose",
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "hemoglobin a1c": "HbA1c",
}

# e.g. "LDL Cholesterol: 142 mg/dL" or "HbA1c 6.1 %" or "Glucose - 105"
_LINE_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z][A-Za-z0-9 /]+?)\s*[:\-]?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|[A-Za-z/]+)?\s*$"
)


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber (imported lazily)."""
    import io

    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _canonical(name: str) -> str | None:
    return _NAME_ALIASES.get(name.strip().lower())


def parse_lab_text(text: str) -> list[LabResultCreate]:
    """Parse known lab results from free text, one per line."""
    labs: list[LabResultCreate] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _LINE_RE.match(line)
        if not match:
            continue
        canonical = _canonical(match.group("name"))
        if canonical is None or canonical in seen:
            continue
        unit, ref_low, ref_high = LAB_COLUMN_SPECS[canonical]
        labs.append(
            LabResultCreate(
                test_name=canonical,
                value=float(match.group("value")),
                unit=unit,
                reference_low=ref_low,
                reference_high=ref_high,
            )
        )
        seen.add(canonical)
    return labs


def parse_patient_from_pdf_text(text: str, *, name: str | None = None) -> PatientCreate:
    """Build a PatientCreate from extracted report text (labs only for now)."""
    return PatientCreate(name=name, labs=parse_lab_text(text))
