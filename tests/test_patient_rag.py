from sqlalchemy.orm import Session

from backend.agents.agent import RuleBasedAgent
from backend.agents.tools import LabReading
from backend.models.orm import LabResult, Patient, Vital
from backend.rag.embedder import LocalHashEmbedder
from backend.rag.patient_docs import build_patient_documents
from backend.rag.retriever import Retriever
from backend.rag.store import VectorStore


def _patient() -> Patient:
    return Patient(id=1, name="Test Person", sex="male", age=55, height_cm=180, weight_kg=100)


def _labs() -> list[LabReading]:
    return [
        LabReading("LDL Cholesterol", 180, "mg/dL", None, 100),
        LabReading("HbA1c", 5.2, "%", 4.0, 5.6),
    ]


def _vitals() -> list[Vital]:
    return [Vital(heart_rate=70, systolic_bp=145, diastolic_bp=92, sleep_hours=6.0)]


def _retriever() -> Retriever:
    return Retriever(embedder=LocalHashEmbedder(dim=512), store=VectorStore())


def test_build_patient_documents_covers_records() -> None:
    docs = build_patient_documents(_patient(), _labs(), _vitals(), bmi=30.9, risk=None)
    sources = {src for _, src in docs}
    assert "patient:demographics" in sources
    assert "patient:lab:ldl_cholesterol" in sources
    assert "patient:lab:hba1c" in sources
    assert any(s.startswith("patient:vitals") for s in sources)
    # The LDL doc carries its value and the abnormal flag.
    ldl = next(text for text, src in docs if src == "patient:lab:ldl_cholesterol")
    assert "180" in ldl and "high" in ldl


def test_search_documents_returns_relevant_fact() -> None:
    docs = build_patient_documents(_patient(), _labs(), _vitals(), bmi=30.9, risk=None)
    retriever = _retriever()

    chol = retriever.search_documents("what about my cholesterol?", docs, top_k=1)
    assert chol
    assert chol[0].source == "patient:lab:ldl_cholesterol"

    # The local embedder is lexical (no stemming), so query terms present in the doc.
    sleep = retriever.search_documents("how is my sleep?", docs, top_k=1)
    assert sleep
    assert sleep[0].source.startswith("patient:vitals")


def test_search_documents_empty_is_safe() -> None:
    assert _retriever().search_documents("anything", [], top_k=3) == []


def test_search_documents_filters_irrelevant() -> None:
    # A question unrelated to any patient fact should return nothing, rather than
    # surfacing an arbitrary doc (e.g. demographics) that merely sorts first.
    docs = build_patient_documents(_patient(), _labs(), _vitals(), bmi=30.9, risk=None)
    hits = _retriever().search_documents("what is the capital of France?", docs, top_k=3)
    assert hits == []


def test_documents_are_patient_scoped() -> None:
    a = build_patient_documents(
        Patient(id=1, name="A", sex="male", age=40, height_cm=170, weight_kg=70),
        [LabReading("LDL Cholesterol", 180, "mg/dL", None, 100)],
        [],
        bmi=24.2,
        risk=None,
    )
    b = build_patient_documents(
        Patient(id=2, name="B", sex="female", age=60, height_cm=160, weight_kg=55),
        [LabReading("LDL Cholesterol", 90, "mg/dL", None, 100)],
        [],
        bmi=21.5,
        risk=None,
    )
    a_text = " ".join(text for text, _ in a)
    b_text = " ".join(text for text, _ in b)
    assert "180" in a_text and "180" not in b_text
    assert "90" in b_text and "90" not in a_text


def test_agent_records_patient_record_tool_call(db_session: Session) -> None:
    patient = Patient(name="Test Person", sex="male", age=55, height_cm=180, weight_kg=100)
    patient.labs = [
        LabResult(test_name="LDL Cholesterol", value=180, unit="mg/dL", reference_high=100)
    ]
    patient.vitals = [Vital(heart_rate=70, systolic_bp=145, diastolic_bp=92, sleep_hours=6.0)]
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    agent = RuleBasedAgent(db=db_session, retriever=_retriever())
    resp = agent.chat(patient.id, "give me an overview")
    called = {tc.tool for tc in resp.tool_calls}
    assert "search_patient_record" in called
