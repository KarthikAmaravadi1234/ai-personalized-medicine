"""Train a baseline diabetes-risk classifier on synthetic labeled data.

The training data is generated from plausible feature distributions with a rule-based
latent risk (driven mainly by HbA1c, fasting glucose, BMI, and age) plus noise. This
is a learning exercise, not a clinically validated model.

Usage:
    python backend/ml/train.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.ml.features import FEATURE_NAMES

MODEL_DIR = _PROJECT_ROOT / "backend" / "ml" / "models"
MODEL_PATH = MODEL_DIR / "diabetes_risk.joblib"

# Approximate (mean, std) per feature for synthetic sampling.
_FEATURE_DIST = {
    "age": (50.0, 16.0),
    "bmi": (27.0, 5.0),
    "fasting_glucose": (98.0, 18.0),
    "hba1c": (5.6, 0.8),
    "ldl": (120.0, 35.0),
    "systolic_bp": (126.0, 16.0),
}


def generate_training_data(n: int = 4000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    columns = []
    for name in FEATURE_NAMES:
        mean, std = _FEATURE_DIST[name]
        columns.append(rng.normal(mean, std, n))
    x = np.column_stack(columns)
    x = np.clip(x, a_min=0.0, a_max=None)

    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    # Latent risk: standardized contributions, dominated by glycemic markers.
    latent = (
        0.05 * (x[:, idx["age"]] - 50.0)
        + 0.12 * (x[:, idx["bmi"]] - 27.0)
        + 0.05 * (x[:, idx["fasting_glucose"]] - 98.0)
        + 1.8 * (x[:, idx["hba1c"]] - 5.6)
        + 0.005 * (x[:, idx["ldl"]] - 120.0)
        + 0.02 * (x[:, idx["systolic_bp"]] - 126.0)
        - 0.5
    )
    noise = rng.normal(0.0, 0.5, n)
    prob = 1.0 / (1.0 + np.exp(-(latent + noise)))
    y = (rng.random(n) < prob).astype(int)
    return x, y


def build_pipeline():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )


def train(n: int = 4000, seed: int = 42) -> tuple[object, dict]:
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    x, y = generate_training_data(n=n, seed=seed)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=seed)

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    proba = pipeline.predict_proba(x_test)[:, 1]
    metrics = {
        "auc": float(roc_auc_score(y_test, proba)),
        "n_train": int(len(x_train)),
        "n_test": int(len(x_test)),
        "positive_rate": float(y.mean()),
    }
    return pipeline, metrics


def save_model(pipeline: object, path: Path = MODEL_PATH) -> None:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "feature_names": FEATURE_NAMES}, path)


def train_and_save(n: int = 4000, seed: int = 42) -> dict:
    pipeline, metrics = train(n=n, seed=seed)
    save_model(pipeline)
    return metrics


if __name__ == "__main__":
    m = train_and_save()
    print(f"Trained diabetes-risk model. Holdout AUC={m['auc']:.3f}, "
          f"positive_rate={m['positive_rate']:.3f}")
    print(f"Saved to {MODEL_PATH}")
