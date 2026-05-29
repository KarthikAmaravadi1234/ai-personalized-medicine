import pytest
from sqlalchemy.orm import Session

from backend.agents.agent import PatientNotFoundError, RuleBasedAgent
from backend.agents.guardrails import apply_guardrails
from backend.agents.tools import (
    LabReading,
    bmi_category,
    calculate_bmi,
    get_patient_labs,
)
from backend.models.orm import LabResult, Patient, Vital
from backend.rag.embedder import LocalHashEmbedder
from backend.rag.retriever import Retriever
from backend.rag.store import VectorStore


def _seed_patient(db: Session) -> Patient:
    patient = Patient(name="Test Person", sex="male", age=55, height_cm=180, weight_kg=100)
    patient.labs = [
        LabResult(test_name="LDL Cholesterol", value=180, unit="mg/dL", reference_high=100),
        LabResult(test_name="HbA1c", value=5.2, unit="%", reference_low=4.0, reference_high=5.6),
    ]
    patient.vitals = [Vital(heart_rate=70, systolic_bp=145, diastolic_bp=92, sleep_hours=6.0)]
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _retriever() -> Retriever:
    r = Retriever(embedder=LocalHashEmbedder(dim=512), store=VectorStore())
    r.index_directory()
    return r


def test_calculate_bmi_and_category() -> None:
    assert calculate_bmi(180, 100) == pytest.approx(30.9, abs=0.1)
    assert bmi_category(calculate_bmi(180, 100)) == "obese"
    assert calculate_bmi(None, 80) is None


def test_lab_reading_flag() -> None:
    high = LabReading("LDL", 180, "mg/dL", None, 100)
    low = LabReading("HDL", 30, "mg/dL", 40, None)
    normal = LabReading("HbA1c", 5.2, "%", 4.0, 5.6)
    assert high.flag == "high"
    assert low.flag == "low"
    assert normal.flag == "normal"


def test_get_patient_labs(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    labs = get_patient_labs(db_session, patient.id)
    assert {lab.test_name for lab in labs} == {"LDL Cholesterol", "HbA1c"}


def test_agent_grounds_in_labs_and_knowledge(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "What does my LDL cholesterol mean?")

    assert resp.patient_id == patient.id
    assert "LDL Cholesterol" in resp.answer
    assert any(c.source == "ldl_cholesterol.md" for c in resp.citations)
    called = {tc.tool for tc in resp.tool_calls}
    assert "get_patient_labs" in called
    assert "search_knowledge" in called


def test_agent_blood_pressure_query_uses_vitals(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "What is my blood pressure?")
    # Targeted answer: just the reading, not the full multi-section summary.
    assert "145/92" in resp.answer
    assert "LDL Cholesterol" not in resp.answer


def test_agent_missing_patient(db_session: Session) -> None:
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    with pytest.raises(PatientNotFoundError):
        agent.chat(9999, "hello")


def test_agent_always_includes_disclaimer(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "how am I doing?")
    assert "not medical advice" in resp.answer.lower()


def test_guardrails_soften_diagnosis() -> None:
    result = apply_guardrails("You have diabetes.", has_citations=True)
    assert "you have diabetes" not in result.text.lower()
    assert result.modified


def test_agent_risk_query_uses_model(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "what is my risk of diabetes?")
    assert any(tc.tool == "get_risk_score" for tc in resp.tool_calls)
    assert "diabetes risk" in resp.answer.lower()


def test_agent_age_query_is_targeted(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "what is my age?")
    assert "55 years old" in resp.answer
    # Targeted: it should NOT dump the labs paragraph for a demographics question.
    assert "Labs outside" not in resp.answer
    assert "LDL Cholesterol" not in resp.answer


def test_agent_specific_lab_query_is_targeted(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "what is my LDL?")
    assert "LDL Cholesterol" in resp.answer
    assert "180" in resp.answer
    assert "above the typical reference range" in resp.answer.lower()
    # No knowledge citation for a plain factual lookup.
    assert resp.citations == []


def test_agent_general_question_gives_summary(db_session: Session) -> None:
    patient = _seed_patient(db_session)
    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "how am I doing?")
    assert "what your data shows" in resp.answer.lower()
