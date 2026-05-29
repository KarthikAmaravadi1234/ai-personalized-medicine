"""Feature engineering for the diabetes-risk baseline model.

Turns a patient's records (demographics, labs, latest vitals) into a fixed feature
vector. Missing values are imputed with population means so the model always has a
complete input. The same feature order is used for training and prediction.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.agents.tools import calculate_bmi, get_patient_labs, get_patient_vitals
from backend.models.orm import Patient

FEATURE_NAMES = ["age", "bmi", "fasting_glucose", "hba1c", "ldl", "systolic_bp"]

# Population means used to impute missing values (rough adult averages).
FEATURE_DEFAULTS: dict[str, float] = {
    "age": 50.0,
    "bmi": 26.0,
    "fasting_glucose": 95.0,
    "hba1c": 5.5,
    "ldl": 120.0,
    "systolic_bp": 125.0,
}

# Map lab test_name -> feature key.
_LAB_TO_FEATURE = {
    "Fasting Glucose": "fasting_glucose",
    "HbA1c": "hba1c",
    "LDL Cholesterol": "ldl",
}


@dataclass
class FeatureSet:
    values: dict[str, float]
    imputed: list[str]

    def vector(self) -> list[float]:
        return [self.values[name] for name in FEATURE_NAMES]


def extract_features(db: Session, patient: Patient) -> FeatureSet:
    raw: dict[str, float | None] = {name: None for name in FEATURE_NAMES}
    raw["age"] = patient.age
    raw["bmi"] = calculate_bmi(patient.height_cm, patient.weight_kg)

    for lab in get_patient_labs(db, patient.id):
        key = _LAB_TO_FEATURE.get(lab.test_name)
        if key is not None:
            raw[key] = lab.value

    vitals = get_patient_vitals(db, patient.id)
    if vitals and vitals[-1].systolic_bp is not None:
        raw["systolic_bp"] = float(vitals[-1].systolic_bp)

    values: dict[str, float] = {}
    imputed: list[str] = []
    for name in FEATURE_NAMES:
        if raw[name] is None:
            values[name] = FEATURE_DEFAULTS[name]
            imputed.append(name)
        else:
            values[name] = float(raw[name])

    return FeatureSet(values=values, imputed=imputed)
