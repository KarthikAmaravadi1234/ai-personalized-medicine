from fastapi.testclient import TestClient

PATIENT = {
    "name": "Chat Person",
    "sex": "male",
    "age": 60,
    "height_cm": 175,
    "weight_kg": 95,
    "labs": [{"test_name": "LDL Cholesterol", "value": 175, "unit": "mg/dL", "reference_high": 100}],
    "vitals": [{"heart_rate": 72, "systolic_bp": 150, "diastolic_bp": 95, "sleep_hours": 6.5}],
}


def _create_patient(client: TestClient) -> int:
    resp = client.post("/patients", json=PATIENT)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_chat_returns_answer_with_citations(client: TestClient) -> None:
    pid = _create_patient(client)
    resp = client.post("/chat", json={"patient_id": pid, "message": "what does my LDL mean?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == pid
    assert body["answer"]
    assert any(c["source"] == "ldl_cholesterol.md" for c in body["citations"])
    assert any(t["tool"] == "get_patient_labs" for t in body["tool_calls"])


def test_chat_missing_patient_404(client: TestClient) -> None:
    resp = client.post("/chat", json={"patient_id": 9999, "message": "hi"})
    assert resp.status_code == 404


def test_chat_validates_message(client: TestClient) -> None:
    pid = _create_patient(client)
    resp = client.post("/chat", json={"patient_id": pid, "message": ""})
    assert resp.status_code == 422
