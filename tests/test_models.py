import pytest
from pydantic import ValidationError

from backend.models.enums import Sex
from backend.models.schemas import PatientCreate, VitalCreate


def test_patient_create_defaults() -> None:
    patient = PatientCreate(name="Ann")
    assert patient.sex == Sex.unknown
    assert patient.labs == []
    assert patient.vitals == []


def test_patient_create_with_nested() -> None:
    patient = PatientCreate(
        name="Bob",
        sex="male",
        age=45,
        height_cm=180,
        weight_kg=82,
        labs=[{"test_name": "LDL", "value": 130, "unit": "mg/dL", "reference_high": 100}],
        vitals=[{"heart_rate": 70, "systolic_bp": 120, "diastolic_bp": 80, "sleep_hours": 7}],
    )
    assert patient.sex == Sex.male
    assert patient.labs[0].test_name == "LDL"
    assert patient.vitals[0].heart_rate == 70


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", 200),
        ("age", -1),
        ("height_cm", 0),
        ("weight_kg", -5),
    ],
)
def test_patient_invalid_bounds(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        PatientCreate(name="X", **{field: value})


def test_invalid_sex_rejected() -> None:
    with pytest.raises(ValidationError):
        PatientCreate(name="X", sex="not-a-sex")


@pytest.mark.parametrize("hours", [-1, 25])
def test_vital_sleep_hours_bounds(hours: float) -> None:
    with pytest.raises(ValidationError):
        VitalCreate(sleep_hours=hours)
