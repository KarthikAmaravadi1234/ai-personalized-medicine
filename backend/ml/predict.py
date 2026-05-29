"""Load the diabetes-risk model and produce interpretable predictions.

If no trained model file exists, a deterministic model is trained in memory on first
use so the endpoint works out of the box. Run ``backend/ml/train.py`` to persist one.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from sqlalchemy.orm import Session

from backend.ml.features import FEATURE_NAMES, FeatureSet, extract_features
from backend.ml.train import MODEL_PATH, train
from backend.models.orm import Patient


@dataclass
class FeatureContribution:
    feature: str
    value: float
    contribution: float


@dataclass
class RiskPrediction:
    probability: float
    risk_level: str
    contributions: list[FeatureContribution]
    model_source: str


def _risk_level(probability: float) -> str:
    if probability < 0.34:
        return "low"
    if probability < 0.67:
        return "moderate"
    return "high"


@lru_cache(maxsize=1)
def _load_bundle() -> dict:
    if MODEL_PATH.exists():
        import joblib

        bundle = joblib.load(MODEL_PATH)
        bundle["source"] = "file"
        return bundle
    # Deterministic in-memory fallback so prediction works without a saved artifact.
    pipeline, _ = train(seed=42)
    return {"pipeline": pipeline, "feature_names": FEATURE_NAMES, "source": "in_memory"}


def reset_model_cache() -> None:
    _load_bundle.cache_clear()


def predict_from_values(values: dict[str, float]) -> RiskPrediction:
    bundle = _load_bundle()
    pipeline = bundle["pipeline"]
    feature_names = bundle["feature_names"]

    vector = np.array([[values[name] for name in feature_names]], dtype=float)
    probability = float(pipeline.predict_proba(vector)[0, 1])

    # Logistic-regression interpretability: contribution = coef * standardized value.
    scaler = pipeline.named_steps["scaler"]
    clf = pipeline.named_steps["clf"]
    standardized = (vector[0] - scaler.mean_) / scaler.scale_
    coefs = clf.coef_[0]
    contributions = [
        FeatureContribution(
            feature=name,
            value=round(float(vector[0][i]), 2),
            contribution=round(float(coefs[i] * standardized[i]), 4),
        )
        for i, name in enumerate(feature_names)
    ]
    contributions.sort(key=lambda c: abs(c.contribution), reverse=True)

    return RiskPrediction(
        probability=round(probability, 4),
        risk_level=_risk_level(probability),
        contributions=contributions,
        model_source=bundle["source"],
    )


def score_patient(db: Session, patient: Patient) -> tuple[FeatureSet, RiskPrediction]:
    """Extract features for a patient and return them alongside the risk prediction."""
    features = extract_features(db, patient)
    prediction = predict_from_values(features.values)
    return features, prediction
