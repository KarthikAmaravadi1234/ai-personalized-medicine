from fastapi.testclient import TestClient


def test_search_endpoint(client: TestClient) -> None:
    resp = client.get("/knowledge/search", params={"q": "elevated LDL cholesterol", "top_k": 3})
    assert resp.status_code == 200
    hits = resp.json()
    assert hits
    assert hits[0]["source"] == "ldl_cholesterol.md"
    assert "score" in hits[0]


def test_ask_endpoint_has_citations(client: TestClient) -> None:
    resp = client.get("/knowledge/ask", params={"q": "how to lower blood pressure"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert any(c["source"] == "hypertension.md" for c in body["citations"])


def test_reindex_endpoint(client: TestClient) -> None:
    resp = client.post("/knowledge/reindex")
    assert resp.status_code == 200
    assert resp.json()["indexed_chunks"] > 0


def test_search_requires_query(client: TestClient) -> None:
    resp = client.get("/knowledge/search")
    assert resp.status_code == 422
