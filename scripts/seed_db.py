"""Seed the database from a synthetic ``patients.json`` file.

Reads the nested JSON produced by ``generate_synthetic_patients.py``, validates it
against ``PatientCreate``, and inserts the patients (with labs and vitals) via the ORM
so the API and web UI have realistic data to show.

Usage:
    python scripts/generate_synthetic_patients.py --count 40 --seed 7 --visits 3
    python scripts/seed_db.py                 # inserts data/synthetic/patients.json
    python scripts/seed_db.py --clear         # wipe existing patients first
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.db.init_db import init_db
from backend.db.session import get_sessionmaker
from backend.models.orm import LabResult, Patient, Vital
from backend.models.schemas import PatientCreate

DEFAULT_INPUT = _PROJECT_ROOT / "data" / "synthetic" / "patients.json"


def _to_orm(data: PatientCreate) -> Patient:
    patient = Patient(
        external_id=data.external_id,
        name=data.name,
        sex=data.sex,
        age=data.age,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
    )
    patient.labs = [LabResult(**lab.model_dump()) for lab in data.labs]
    patient.vitals = [Vital(**vital.model_dump()) for vital in data.vitals]
    return patient


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the database from synthetic patients JSON.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"Input JSON (default: {DEFAULT_INPUT})")
    parser.add_argument("--clear", action="store_true", help="Delete existing patients before inserting")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}. Run generate_synthetic_patients.py first.")

    raw = json.loads(args.input.read_text())
    patients = [PatientCreate.model_validate(item) for item in raw]

    init_db()
    session = get_sessionmaker()()
    try:
        if args.clear:
            deleted = session.query(Patient).delete()
            session.commit()
            print(f"Cleared {deleted} existing patient(s).")

        session.add_all(_to_orm(p) for p in patients)
        session.commit()
        print(f"Inserted {len(patients)} patient(s) from {args.input}.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
