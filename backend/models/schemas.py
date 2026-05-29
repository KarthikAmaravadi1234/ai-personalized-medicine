from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import Sex


class LabResultBase(BaseModel):
    test_name: str = Field(..., max_length=128)
    value: float
    unit: str | None = Field(None, max_length=32)
    reference_low: float | None = None
    reference_high: float | None = None
    measured_at: date | None = None


class LabResultCreate(LabResultBase):
    pass


class LabResultRead(LabResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    created_at: datetime


class VitalBase(BaseModel):
    heart_rate: int | None = Field(None, ge=0, le=400)
    systolic_bp: int | None = Field(None, ge=0, le=400)
    diastolic_bp: int | None = Field(None, ge=0, le=400)
    steps: int | None = Field(None, ge=0)
    sleep_hours: float | None = Field(None, ge=0, le=24)
    recorded_at: date | None = None


class VitalCreate(VitalBase):
    pass


class VitalRead(VitalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    created_at: datetime


class PatientBase(BaseModel):
    external_id: str | None = Field(None, max_length=64)
    name: str | None = Field(None, max_length=255)
    sex: Sex = Sex.unknown
    age: int | None = Field(None, ge=0, le=150)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)


class PatientCreate(PatientBase):
    labs: list[LabResultCreate] = Field(default_factory=list)
    vitals: list[VitalCreate] = Field(default_factory=list)


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    labs: list[LabResultRead] = Field(default_factory=list)
    vitals: list[VitalRead] = Field(default_factory=list)


class PatientSummary(BaseModel):
    """Lightweight patient view for list endpoints (no nested labs/vitals)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None = None
    name: str | None = None
    sex: Sex
    age: int | None = None
    created_at: datetime
