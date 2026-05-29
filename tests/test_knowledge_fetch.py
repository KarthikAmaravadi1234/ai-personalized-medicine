import json

import pytest

from backend.rag.embedder import LocalHashEmbedder
from backend.rag.retriever import Retriever, _strip_frontmatter
from scripts import fetch_knowledge as fk

WIKI_JSON = json.dumps(
    {
        "query": {
            "pages": {
                "123": {
                    "title": "Glycated hemoglobin",
                    "extract": "HbA1c reflects average blood glucose.\n\n== Interpretation ==\n\nNormal is below 5.7 percent.",
                }
            }
        }
    }
)

MEDLINE_XML = (
    "<nlmSearchResult><list>"
    '<document url="https://medlineplus.gov/diabetes.html">'
    '<content name="title">Diabetes</content>'
    '<content name="FullSummary">&lt;p&gt;Diabetes affects blood sugar.&lt;/p&gt;</content>'
    "</document></list></nlmSearchResult>"
)


def test_html_to_text_strips_tags():
    assert fk.html_to_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_wiki_sections_to_markdown():
    out = fk.wiki_sections_to_markdown("Intro.\n\n== History ==\n\nMore.", max_words=None)
    assert "## History" in out
    assert "==" not in out


def test_fetch_wikipedia(monkeypatch):
    monkeypatch.setattr(fk, "_http_get", lambda url, params=None: WIKI_JSON)
    result = fk.fetch_wikipedia("Glycated hemoglobin")
    assert result["title"] == "Glycated hemoglobin"
    assert result["license"] == "CC BY-SA 4.0"
    assert "average blood glucose" in result["text"]
    assert "## Interpretation" in result["text"]
    assert result["source_url"].endswith("Glycated_hemoglobin")


def test_fetch_medlineplus(monkeypatch):
    monkeypatch.setattr(fk, "_http_get", lambda url, params=None: MEDLINE_XML)
    result = fk.fetch_medlineplus("diabetes")
    assert result["title"] == "Diabetes"
    assert "blood sugar" in result["text"]
    assert "public domain" in result["license"].lower()


def test_write_topic_and_frontmatter_round_trip(tmp_path):
    fetched = {
        "title": "Glycated hemoglobin",
        "text": "HbA1c reflects average glucose.",
        "source": "wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Glycated_hemoglobin",
        "license": "CC BY-SA 4.0",
    }
    entry = fk.write_topic({"slug": "hba1c", "query": "A1C"}, fetched, tmp_path, "2026-05-29")
    assert entry["slug"] == "hba1c"

    raw = (tmp_path / "hba1c.md").read_text()
    assert raw.startswith("---")
    assert "license: CC BY-SA 4.0" in raw

    stripped = _strip_frontmatter(raw)
    assert "license:" not in stripped
    assert "HbA1c reflects average glucose." in stripped


class _FakeResp:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_http_get_retries_on_429(monkeypatch):
    responses = [
        _FakeResp(429, headers={"Retry-After": "0"}),
        _FakeResp(200, text="ok"),
    ]
    calls = {"n": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["n"] += 1
        return responses.pop(0)

    import httpx

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)

    assert fk._http_get("https://example.test") == "ok"
    assert calls["n"] == 2


def test_merge_manifest_replaces_by_slug():
    existing = [
        {"slug": "hba1c", "title": "Old"},
        {"slug": "hypertension", "title": "BP"},
    ]
    merged = fk.merge_manifest(existing, [{"slug": "hba1c", "title": "New"}])
    by_slug = {e["slug"]: e for e in merged}
    assert by_slug["hba1c"]["title"] == "New"
    assert by_slug["hypertension"]["title"] == "BP"
    assert [e["slug"] for e in merged] == ["hba1c", "hypertension"]


def test_retriever_ignores_frontmatter(tmp_path):
    (tmp_path / "doc.md").write_text(
        "---\ntitle: Test\nlicense: CC BY-SA 4.0\nsource_url: http://x\n---\n\n"
        "Cholesterol is a waxy substance found in blood.\n"
    )
    retriever = Retriever(embedder=LocalHashEmbedder())
    count = retriever.index_directory(tmp_path)
    assert count >= 1
    hits = retriever.search("cholesterol", top_k=1)
    assert hits
    assert "license" not in hits[0].text.lower()
    assert "cholesterol" in hits[0].text.lower()
