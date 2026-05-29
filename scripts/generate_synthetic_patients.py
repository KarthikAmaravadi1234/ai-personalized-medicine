"""Generate synthetic patient records for local development.

Produces fake demographics, labs, and vitals. Output is written to
``data/synthetic/`` as both nested JSON (matching ``PatientCreate``) and a flat
CSV (one row per patient, demographics + key lab values).

Usage:
    python scripts/generate_synthetic_patients.py --count 30 --seed 42

This data is entirely fake. Never commit real PHI.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.models.enums import Sex
from backend.models.schemas import LabResultCreate, PatientCreate, VitalCreate

DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "synthetic"

FIRST_NAMES = [
    "Ava", "Liam", "Maya", "Noah", "Sofia", "Ethan", "Zoe", "Lucas",
    "Mia", "Owen", "Aria", "Leo", "Nora", "Eli", "Ivy", "Kai",
    "Ruth", "Sam", "Tara", "Omar",
]
LAST_NAMES = [
    "Patel", "Nguyen", "Garcia", "Smith", "Kim", "Lopez", "Khan", "Chen",
    "Johnson", "Singh", "Rossi", "Haddad", "Okafor", "Silva", "Cohen", "Mehta",
]

# (test_name, unit, mean, stdev, reference_low, reference_high)
LAB_SPECS = [
    ("LDL Cholesterol", "mg/dL", 120, 35, None, 100),
    ("HDL Cholesterol", "mg/dL", 55, 15, 40, None),
    ("Total Cholesterol", "mg/dL", 190, 40, None, 200),
    ("Triglycerides", "mg/dL", 130, 60, None, 150),
    ("Fasting Glucose", "mg/dL", 95, 20, 70, 99),
    ("HbA1c", "%", 5.6, 0.9, 4.0, 5.6),
]


def _round_lab(test_name: str, value: float) -> float:
    return round(value, 1) if test_name == "HbA1c" else round(value)


def _make_labs(rng: random.Random, measured_at: date) -> list[LabResultCreate]:
    labs: list[LabResultCreate] = []
    for name, unit, mean, stdev, ref_low, ref_high in LAB_SPECS:
        raw = max(0.0, rng.gauss(mean, stdev))
        labs.append(
            LabResultCreate(
                test_name=name,
                value=_round_lab(name, raw),
                unit=unit,
                reference_low=ref_low,
                reference_high=ref_high,
                measured_at=measured_at,
            )
        )
    return labs


def _make_vitals(rng: random.Random, recorded_at: date) -> list[VitalCreate]:
    return [
        VitalCreate(
            heart_rate=rng.randint(55, 100),
            systolic_bp=rng.randint(105, 150),
            diastolic_bp=rng.randint(65, 95),
            steps=rng.randint(2000, 15000),
            sleep_hours=round(rng.uniform(4.5, 9.0), 1),
            recorded_at=recorded_at,
        )
    ]


def generate_patients(count: int, rng: random.Random) -> list[PatientCreate]:
    today = date.today()
    patients: list[PatientCreate] = []
    for i in range(count):
        sex = rng.choice([Sex.male, Sex.female])
        age = rng.randint(18, 90)
        if sex == Sex.male:
            height_cm = round(rng.gauss(176, 7), 1)
        else:
            height_cm = round(rng.gauss(163, 6), 1)
        bmi = rng.gauss(26, 4)
        weight_kg = round(max(40.0, bmi * (height_cm / 100) ** 2), 1)
        measured_at = today - timedelta(days=rng.randint(0, 365))

        patients.append(
            PatientCreate(
                external_id=f"SYN-{i + 1:04d}",
                name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                sex=sex,
                age=age,
                height_cm=height_cm,
                weight_kg=weight_kg,
                labs=_make_labs(rng, measured_at),
                vitals=_make_vitals(rng, measured_at),
            )
        )
    return patients


def write_json(patients: list[PatientCreate], path: Path) -> None:
    payload = [p.model_dump(mode="json") for p in patients]
    path.write_text(json.dumps(payload, indent=2))


def write_csv(patients: list[PatientCreate], path: Path) -> None:
    lab_columns = [name for name, *_ in LAB_SPECS]
    fieldnames = [
        "external_id", "name", "sex", "age", "height_cm", "weight_kg",
        *lab_columns,
        "heart_rate", "systolic_bp", "diastolic_bp", "steps", "sleep_hours",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in patients:
            lab_by_name = {lab.test_name: lab.value for lab in p.labs}
            vital = p.vitals[0] if p.vitals else None
            row = {
                "external_id": p.external_id,
                "name": p.name,
                "sex": p.sex.value,
                "age": p.age,
                "height_cm": p.height_cm,
                "weight_kg": p.weight_kg,
                **{name: lab_by_name.get(name) for name in lab_columns},
                "heart_rate": vital.heart_rate if vital else None,
                "systolic_bp": vital.systolic_bp if vital else None,
                "diastolic_bp": vital.diastolic_bp if vital else None,
                "steps": vital.steps if vital else None,
                "sleep_hours": vital.sleep_hours if vital else None,
            }
            writer.writerow(row)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic patient records.")
    parser.add_argument("--count", type=int, default=30, help="Number of patients (default: 30)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    rng = random.Random(args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    patients = generate_patients(args.count, rng)

    json_path = args.output_dir / "patients.json"
    csv_path = args.output_dir / "patients.csv"
    write_json(patients, json_path)
    write_csv(patients, csv_path)

    print(f"Generated {len(patients)} patients:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")


if __name__ == "__main__":
    main()
