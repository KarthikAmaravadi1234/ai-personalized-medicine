import numpy as np

from scripts.generate_synthetic_patients import (
    _latest_labs,
    generate_patients,
    write_cohort_csv,
)


def _corr(a, b):
    return float(np.corrcoef(np.array(a), np.array(b))[0, 1])


def test_labs_are_clinically_correlated():
    rng = np.random.default_rng(123)
    records = generate_patients(400, rng, visits=2)

    glucose, hba1c, bmi, ldl, hdl = [], [], [], [], []
    for patient, meta in records:
        labs = _latest_labs(patient)
        glucose.append(labs["Fasting Glucose"])
        hba1c.append(labs["HbA1c"])
        ldl.append(labs["LDL Cholesterol"])
        hdl.append(labs["HDL Cholesterol"])
        bmi.append(meta["features"]["bmi"])

    # Positive metabolic correlations
    assert _corr(glucose, hba1c) > 0.2
    assert _corr(bmi, hba1c) > 0.2
    assert _corr(bmi, ldl) > 0.15
    # HDL is protective -> inversely related to BMI
    assert _corr(hdl, bmi) < 0.0


def test_longitudinal_visit_counts():
    rng = np.random.default_rng(7)
    records = generate_patients(20, rng, visits=3)
    for patient, _meta in records:
        assert len(patient.labs) == 3 * 6  # 6 lab specs per visit
        assert len(patient.vitals) == 3


def test_labels_present_and_consistent():
    rng = np.random.default_rng(42)
    records = generate_patients(300, rng, visits=1)

    positives = 0
    for patient, meta in records:
        assert meta["conditions"], "every patient should have at least one condition label"
        assert meta["diabetes_label"] in (0, 1)
        labs = _latest_labs(patient)
        if meta["diabetes_label"] == 1:
            assert labs["HbA1c"] >= 6.5 or labs["Fasting Glucose"] >= 126
            positives += 1
    assert positives > 0  # the cohort should contain some diabetic patients


def test_cohort_csv_has_feature_columns(tmp_path):
    rng = np.random.default_rng(1)
    records = generate_patients(10, rng, visits=1)
    path = tmp_path / "cohort.csv"
    write_cohort_csv(records, path)

    header = path.read_text().splitlines()[0]
    assert header == "age,bmi,fasting_glucose,hba1c,ldl,systolic_bp,diabetes_label"
