from fastapi.testclient import TestClient

SAMPLE_CSV = (
    "external_id,name,sex,age,height_cm,weight_kg,LDL Cholesterol,HbA1c,"
    "heart_rate,systolic_bp,diastolic_bp,steps,sleep_hours\n"
    "SYN-0001,Ann Patel,female,34,165,60,140,5.4,72,118,76,8000,7.5\n"
    "SYN-0002,Bob Kim,male,58,178,90,95,6.1,68,135,85,5000,6.0\n"
)


def _upload(client: TestClient, csv_text: str = SAMPLE_CSV):
    return client.post(
        "/patients/upload",
        files={"file": ("patients.csv", csv_text.encode(), "text/csv")},
    )


def test_create_patient_json(client: TestClient) -> None:
    resp = client.post(
        "/patients",
        json={"name": "Solo", "sex": "male", "age": 50, "labs": [{"test_name": "LDL", "value": 99}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] >= 1
    assert body["name"] == "Solo"
    assert body["labs"][0]["test_name"] == "LDL"


def test_upload_csv_creates_patients(client: TestClient) -> None:
    resp = _upload(client)
    assert resp.status_code == 201
    assert resp.json() == {"created": 2, "errors": []}


def test_list_patients(client: TestClient) -> None:
    _upload(client)
    resp = client.get("/patients")
    assert resp.status_code == 200
    externals = [p["external_id"] for p in resp.json()]
    assert externals == ["SYN-0001", "SYN-0002"]


def test_list_pagination(client: TestClient) -> None:
    _upload(client)
    resp = client.get("/patients", params={"limit": 1, "offset": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["external_id"] == "SYN-0002"


def test_get_patient_with_nested(client: TestClient) -> None:
    _upload(client)
    resp = client.get("/patients/1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["labs"]) == 2
    assert len(body["vitals"]) == 1


def test_get_patient_labs(client: TestClient) -> None:
    _upload(client)
    resp = client.get("/patients/1/labs")
    assert resp.status_code == 200
    assert {lab["test_name"] for lab in resp.json()} == {"LDL Cholesterol", "HbA1c"}


def test_get_missing_patient_404(client: TestClient) -> None:
    resp = client.get("/patients/9999")
    assert resp.status_code == 404


def test_upload_rejects_non_csv(client: TestClient) -> None:
    resp = client.post(
        "/patients/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415
