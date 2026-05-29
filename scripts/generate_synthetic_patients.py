"""Generate synthetic patient records for local development.

Produces fake demographics, labs, and vitals with *clinically correlated* values
(a shared latent metabolic-risk factor drives glucose, HbA1c, lipids, BMI, and blood
pressure together), optional longitudinal visits, and derived condition labels.

Outputs are written to ``data/synthetic/``:
- ``patients.json``  - nested JSON matching ``PatientCreate`` (for the API / DB seed)
- ``patients.csv``   - one row per patient (demographics + latest labs/vitals + conditions)
- ``cohort_labeled.csv`` - ML feature columns + ``diabetes_label`` (for model training)

Usage:
    python scripts/generate_synthetic_patients.py --count 30 --seed 42 --visits 3

This data is entirely fake. Never commit real PHI.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

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

# Per-measurement statistics: mean, std, reference range, and rounding precision.
# (test_name, unit, mean, std, ref_low, ref_high, round_digits)
LAB_SPECS = [
    ("LDL Cholesterol", "mg/dL", 120.0, 35.0, None, 100.0, 0),
    ("HDL Cholesterol", "mg/dL", 55.0, 15.0, 40.0, None, 0),
    ("Total Cholesterol", "mg/dL", 190.0, 40.0, None, 200.0, 0),
    ("Triglycerides", "mg/dL", 130.0, 60.0, None, 150.0, 0),
    ("Fasting Glucose", "mg/dL", 95.0, 18.0, 70.0, 99.0, 0),
    ("HbA1c", "%", 5.6, 0.8, 4.0, 5.6, 1),
]

# Distribution stats for derived (non-lab) factors.
BMI_MEAN, BMI_STD = 27.0, 5.0
SYS_MEAN, SYS_STD = 126.0, 16.0
DIA_MEAN, DIA_STD = 80.0, 10.0

# Factor loadings on the latent metabolic-risk factor (z) and the age factor (a).
# value_std = Lz * z + La * a + sqrt(1 - Lz^2 - La^2) * noise  (keeps unit variance).
# Positive z raises cardiometabolic markers; HDL loads negatively (protective).
LOADINGS: dict[str, tuple[float, float]] = {
    "bmi": (0.70, 0.10),
    "Fasting Glucose": (0.60, 0.20),
    "HbA1c": (0.65, 0.20),
    "LDL Cholesterol": (0.45, 0.15),
    "Total Cholesterol": (0.50, 0.15),
    "Triglycerides": (0.55, 0.10),
    "HDL Cholesterol": (-0.55, -0.10),
    "systolic_bp": (0.40, 0.45),
    "diastolic_bp": (0.40, 0.25),
}

# Per-visit drift (in std units) modelling slow disease progression over time.
TREND: dict[str, float] = {
    "bmi": 0.06,
    "Fasting Glucose": 0.12,
    "HbA1c": 0.12,
    "Triglycerides": 0.05,
}

ML_FEATURE_COLUMNS = ["age", "bmi", "fasting_glucose", "hba1c", "ldl", "systolic_bp"]


def _idiosyncratic(loading_z: float, loading_a: float) -> float:
    """Residual std so each standardized value keeps approximately unit variance."""
    return float(np.sqrt(max(0.0, 1.0 - loading_z**2 - loading_a**2)))


def _base_standardized(rng: np.random.Generator, z: float, a: float) -> dict[str, float]:
    """One standardized draw per factor, correlated through the shared z and a."""
    out: dict[str, float] = {}
    for key, (lz, la) in LOADINGS.items():
        out[key] = lz * z + la * a + _idiosyncratic(lz, la) * rng.normal()
    return out


def _scale_lab(name: str, std_value: float) -> float:
    for test_name, _unit, mean, std, _lo, _hi, digits in LAB_SPECS:
        if test_name == name:
            raw = max(0.0, mean + std * std_value)
            return round(raw, digits) if digits else round(raw)
    raise KeyError(name)


def _lab_spec(name: str) -> tuple[str, str, float, float, float | None, float | None, int]:
    for spec in LAB_SPECS:
        if spec[0] == name:
            return spec
    raise KeyError(name)


def _make_visit_labs(
    base_std: dict[str, float],
    visit_offset: float,
    drift_dir: float,
    rng: np.random.Generator,
    measured_at: date,
) -> list[LabResultCreate]:
    labs: list[LabResultCreate] = []
    for name, unit, _mean, _std, ref_low, ref_high, _digits in LAB_SPECS:
        drift = TREND.get(name, 0.0) * visit_offset * drift_dir
        std_value = base_std[name] + drift + rng.normal(0.0, 0.15)
        labs.append(
            LabResultCreate(
                test_name=name,
                value=_scale_lab(name, std_value),
                unit=unit,
                reference_low=ref_low,
                reference_high=ref_high,
                measured_at=measured_at,
            )
        )
    return labs


def _bmi_for_visit(base_std: dict[str, float], visit_offset: float, drift_dir: float, rng: np.random.Generator) -> float:
    drift = TREND["bmi"] * visit_offset * drift_dir
    std_value = base_std["bmi"] + drift + rng.normal(0.0, 0.1)
    return float(max(15.0, BMI_MEAN + BMI_STD * std_value))


def _make_visit_vital(
    base_std: dict[str, float],
    rng: np.random.Generator,
    recorded_at: date,
) -> VitalCreate:
    systolic = int(np.clip(SYS_MEAN + SYS_STD * (base_std["systolic_bp"] + rng.normal(0, 0.15)), 90, 200))
    diastolic = int(np.clip(DIA_MEAN + DIA_STD * (base_std["diastolic_bp"] + rng.normal(0, 0.15)), 55, 120))
    return VitalCreate(
        heart_rate=int(rng.integers(55, 100)),
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        steps=int(rng.integers(2000, 15000)),
        sleep_hours=round(float(rng.uniform(4.5, 9.0)), 1),
        recorded_at=recorded_at,
    )


def _classify(latest_labs: dict[str, float], latest_vital: VitalCreate) -> tuple[list[str], int]:
    """Derive self-consistent condition labels from the most recent measurements."""
    conditions: list[str] = []
    hba1c = latest_labs.get("HbA1c", 0.0)
    glucose = latest_labs.get("Fasting Glucose", 0.0)
    ldl = latest_labs.get("LDL Cholesterol", 0.0)
    trig = latest_labs.get("Triglycerides", 0.0)
    hdl = latest_labs.get("HDL Cholesterol", 999.0)

    diabetic = hba1c >= 6.5 or glucose >= 126
    if diabetic:
        conditions.append("diabetic")
    elif hba1c >= 5.7 or glucose >= 100:
        conditions.append("prediabetic")

    if (latest_vital.systolic_bp or 0) >= 130 or (latest_vital.diastolic_bp or 0) >= 80:
        conditions.append("hypertension")
    if ldl >= 160 or trig >= 200 or hdl < 40:
        conditions.append("dyslipidemia")
    if not conditions:
        conditions.append("healthy")

    return conditions, int(diabetic)


def generate_patients(
    count: int, rng: np.random.Generator, visits: int = 1
) -> list[tuple[PatientCreate, dict]]:
    today = date.today()
    visits = max(1, visits)
    records: list[tuple[PatientCreate, dict]] = []

    for i in range(count):
        sex = Sex.male if rng.random() < 0.5 else Sex.female
        age = int(rng.integers(18, 91))
        height_cm = round(float(rng.normal(176 if sex == Sex.male else 163, 7 if sex == Sex.male else 6)), 1)

        z = float(rng.normal())
        a = (age - 50.0) / 16.0
        drift_dir = 1.0 if z > 0 else -0.3
        base_std = _base_standardized(rng, z, a)

        all_labs: list[LabResultCreate] = []
        all_vitals: list[VitalCreate] = []
        latest_labs: dict[str, float] = {}
        latest_vital: VitalCreate | None = None
        latest_bmi = BMI_MEAN

        # Oldest visit first; newest visit (largest offset) is "current".
        for k in range(visits):
            visit_offset = float(k)
            measured_at = today - timedelta(days=(visits - 1 - k) * 150 + int(rng.integers(0, 45)))
            visit_labs = _make_visit_labs(base_std, visit_offset, drift_dir, rng, measured_at)
            visit_vital = _make_visit_vital(base_std, rng, measured_at)
            all_labs.extend(visit_labs)
            all_vitals.append(visit_vital)
            latest_labs = {lab.test_name: lab.value for lab in visit_labs}
            latest_vital = visit_vital
            latest_bmi = _bmi_for_visit(base_std, visit_offset, drift_dir, rng)

        weight_kg = round(max(40.0, latest_bmi * (height_cm / 100) ** 2), 1)
        assert latest_vital is not None
        conditions, diabetes_label = _classify(latest_labs, latest_vital)

        patient = PatientCreate(
            external_id=f"SYN-{i + 1:04d}",
            name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            sex=sex,
            age=age,
            height_cm=height_cm,
            weight_kg=weight_kg,
            labs=all_labs,
            vitals=all_vitals,
        )
        meta = {
            "conditions": conditions,
            "diabetes_label": diabetes_label,
            "features": {
                "age": float(age),
                "bmi": round(latest_bmi, 1),
                "fasting_glucose": latest_labs.get("Fasting Glucose"),
                "hba1c": latest_labs.get("HbA1c"),
                "ldl": latest_labs.get("LDL Cholesterol"),
                "systolic_bp": float(latest_vital.systolic_bp) if latest_vital.systolic_bp else None,
            },
        }
        records.append((patient, meta))
    return records


def _latest_labs(patient: PatientCreate) -> dict[str, float]:
    latest: dict[str, tuple[date, float]] = {}
    for lab in patient.labs:
        d = lab.measured_at or date.min
        if lab.test_name not in latest or d >= latest[lab.test_name][0]:
            latest[lab.test_name] = (d, lab.value)
    return {name: value for name, (_d, value) in latest.items()}


def _latest_vital(patient: PatientCreate) -> VitalCreate | None:
    if not patient.vitals:
        return None
    return sorted(patient.vitals, key=lambda v: v.recorded_at or date.min)[-1]


def write_json(records: list[tuple[PatientCreate, dict]], path: Path) -> None:
    payload = [p.model_dump(mode="json") for p, _meta in records]
    path.write_text(json.dumps(payload, indent=2))


def write_csv(records: list[tuple[PatientCreate, dict]], path: Path) -> None:
    lab_columns = [name for name, *_ in LAB_SPECS]
    fieldnames = [
        "external_id", "name", "sex", "age", "height_cm", "weight_kg",
        *lab_columns,
        "heart_rate", "systolic_bp", "diastolic_bp", "steps", "sleep_hours",
        "conditions",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for patient, meta in records:
            labs = _latest_labs(patient)
            vital = _latest_vital(patient)
            row = {
                "external_id": patient.external_id,
                "name": patient.name,
                "sex": patient.sex.value,
                "age": patient.age,
                "height_cm": patient.height_cm,
                "weight_kg": patient.weight_kg,
                **{name: labs.get(name) for name in lab_columns},
                "heart_rate": vital.heart_rate if vital else None,
                "systolic_bp": vital.systolic_bp if vital else None,
                "diastolic_bp": vital.diastolic_bp if vital else None,
                "steps": vital.steps if vital else None,
                "sleep_hours": vital.sleep_hours if vital else None,
                "conditions": ";".join(meta["conditions"]),
            }
            writer.writerow(row)


def write_cohort_csv(records: list[tuple[PatientCreate, dict]], path: Path) -> None:
    """Feature matrix + label, aligned with backend.ml.features.FEATURE_NAMES."""
    fieldnames = [*ML_FEATURE_COLUMNS, "diabetes_label"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for _patient, meta in records:
            row = dict(meta["features"])
            row["diabetes_label"] = meta["diabetes_label"]
            writer.writerow(row)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic patient records.")
    parser.add_argument("--count", type=int, default=30, help="Number of patients (default: 30)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--visits", type=int, default=1, help="Lab/vital visits per patient (default: 1)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    rng = np.random.default_rng(args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = generate_patients(args.count, rng, visits=args.visits)

    json_path = args.output_dir / "patients.json"
    csv_path = args.output_dir / "patients.csv"
    cohort_path = args.output_dir / "cohort_labeled.csv"
    write_json(records, json_path)
    write_csv(records, csv_path)
    write_cohort_csv(records, cohort_path)

    positives = sum(meta["diabetes_label"] for _p, meta in records)
    print(f"Generated {len(records)} patients ({args.visits} visit(s) each):")
    print(f"  JSON:   {json_path}")
    print(f"  CSV:    {csv_path}")
    print(f"  Cohort: {cohort_path}  (diabetes positives: {positives})")


if __name__ == "__main__":
    main()
