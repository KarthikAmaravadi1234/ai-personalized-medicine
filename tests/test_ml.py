from sqlalchemy.orm import Session

from backend.ml.features import FEATURE_NAMES, extract_features
from backend.ml.predict import predict_from_values, score_patient
from backend.ml.train import generate_training_data, train
from backend.models.orm import LabResult, Patient, Vital


def test_training_data_shape_and_labels() -> None:
    x, y = generate_training_data(n=500, seed=1)
    assert x.shape == (500, len(FEATURE_NAMES))
    assert set(y.tolist()) <= {0, 1}


def test_model_trains_with_reasonable_auc() -> None:
    _, metrics = train(n=2000, seed=7)
    assert metrics["auc"] > 0.7


def test_prediction_orders_risk_correctly() -> None:
    low = predict_from_values(
        {"age": 28, "bmi": 21, "fasting_glucose": 84, "hba1c": 4.9, "ldl": 90, "systolic_bp": 112}
    )
    high = predict_from_values(
        {"age": 66, "bmi": 35, "fasting_glucose": 145, "hba1c": 7.8, "ldl": 175, "systolic_bp": 152}
    )
    assert low.probability < high.probability
    assert low.risk_level == "low"
    assert high.risk_level == "high"
    # Glycemic markers should dominate the explanation.
    assert high.contributions[0].feature in {"hba1c", "fasting_glucose"}


def test_extract_features_imputes_missing(db_session: Session) -> None:
    patient = Patient(name="Sparse", sex="male", age=40)  # no labs/vitals/height/weight
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    features = extract_features(db_session, patient)
    assert features.values["age"] == 40
    # bmi, glucose, hba1c, ldl, systolic_bp all imputed
    assert "bmi" in features.imputed
    assert "hba1c" in features.imputed


def test_score_patient_uses_record(db_session: Session) -> None:
    patient = Patient(name="Risky", sex="male", age=65, height_cm=175, weight_kg=105)
    patient.labs = [
        LabResult(test_name="HbA1c", value=7.9, unit="%", reference_high=5.6),
        LabResult(test_name="Fasting Glucose", value=148, unit="mg/dL", reference_high=99),
    ]
    patient.vitals = [Vital(systolic_bp=150, diastolic_bp=95)]
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    features, prediction = score_patient(db_session, patient)
    assert features.values["hba1c"] == 7.9
    assert prediction.risk_level == "high"
