from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db.session import get_db
from backend.ingestion.csv_parser import parse_patients_csv
from backend.ingestion.pdf_parser import extract_text_from_pdf, parse_patient_from_pdf_text
from backend.ml.predict import score_patient
from backend.models.orm import LabResult, Patient, Vital
from backend.models.schemas import (
    LabResultRead,
    PatientCreate,
    PatientRead,
    PatientSummary,
)

router = APIRouter(prefix="/patients", tags=["patients"])


class FeatureContributionOut(BaseModel):
    feature: str
    value: float
    contribution: float


class RiskResponse(BaseModel):
    patient_id: int
    condition: str
    probability: float
    risk_level: str
    model_source: str
    imputed_features: list[str]
    contributions: list[FeatureContributionOut]


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


def _get_patient_or_404(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> Patient:
    patient = _to_orm(payload)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/upload", status_code=201)
def upload_patients_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", None} and not (
        file.filename and file.filename.endswith(".csv")
    ):
        raise HTTPException(status_code=415, detail="Expected a CSV file.")

    content = file.file.read()
    result = parse_patients_csv(content)

    if not result.patients and result.errors:
        raise HTTPException(status_code=422, detail=result.errors)

    orm_patients = [_to_orm(p) for p in result.patients]
    db.add_all(orm_patients)
    db.commit()

    return {
        "created": len(orm_patients),
        "errors": result.errors,
    }


@router.post("/upload/pdf", response_model=PatientRead, status_code=201)
def upload_patient_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Patient:
    if not (file.filename and file.filename.lower().endswith(".pdf")) and file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Expected a PDF file.")

    data = file.file.read()
    try:
        text = extract_text_from_pdf(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {exc}") from exc

    name = file.filename.rsplit(".", 1)[0] if file.filename else None
    parsed = parse_patient_from_pdf_text(text, name=name)
    if not parsed.labs:
        raise HTTPException(status_code=422, detail="No recognizable lab values found in the PDF.")

    patient = _to_orm(parsed)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientSummary])
def list_patients(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.id).offset(offset).limit(limit)
    return list(db.scalars(stmt))


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db)) -> Patient:
    stmt = (
        select(Patient)
        .where(Patient.id == patient_id)
        .options(selectinload(Patient.labs), selectinload(Patient.vitals))
    )
    patient = db.scalars(stmt).first()
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


@router.get("/{patient_id}/labs", response_model=list[LabResultRead])
def get_patient_labs(patient_id: int, db: Session = Depends(get_db)) -> list[LabResult]:
    _get_patient_or_404(db, patient_id)
    stmt = select(LabResult).where(LabResult.patient_id == patient_id).order_by(LabResult.id)
    return list(db.scalars(stmt))


@router.get("/{patient_id}/risk", response_model=RiskResponse)
def get_patient_risk(patient_id: int, db: Session = Depends(get_db)) -> RiskResponse:
    patient = _get_patient_or_404(db, patient_id)
    features, prediction = score_patient(db, patient)
    return RiskResponse(
        patient_id=patient_id,
        condition="type_2_diabetes",
        probability=prediction.probability,
        risk_level=prediction.risk_level,
        model_source=prediction.model_source,
        imputed_features=features.imputed,
        contributions=[FeatureContributionOut(**vars(c)) for c in prediction.contributions],
    )
