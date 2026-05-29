"""Streamlit UI for the AI Personalized Medicine API.

Run the API first (uvicorn backend.api.main:app --reload), then:
    streamlit run frontend/app.py

Set API_BASE_URL to point at a non-default backend.
"""

import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0

st.set_page_config(page_title="AI Personalized Medicine", page_icon="🧬", layout="wide")


def api_get(path: str, **params):
    resp = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, json=None, files=None):
    resp = httpx.post(f"{API_BASE_URL}{path}", json=json, files=files, timeout=TIMEOUT)
    return resp


def check_api() -> tuple[bool, str]:
    try:
        body = api_get("/health")
        return True, body.get("status", "unknown")
    except Exception as exc:  # noqa: BLE001 - surface any connection error to the user
        return False, str(exc)


def patients_page() -> None:
    st.header("Patients")

    with st.expander("Upload patient data"):
        col1, col2 = st.columns(2)
        with col1:
            csv_file = st.file_uploader("CSV of patients", type=["csv"], key="csv")
            if csv_file and st.button("Upload CSV"):
                resp = api_post(
                    "/patients/upload",
                    files={"file": (csv_file.name, csv_file.getvalue(), "text/csv")},
                )
                if resp.status_code == 201:
                    st.success(f"Uploaded: {resp.json()}")
                else:
                    st.error(f"{resp.status_code}: {resp.text}")
        with col2:
            pdf_file = st.file_uploader("PDF lab report", type=["pdf"], key="pdf")
            if pdf_file and st.button("Upload PDF"):
                resp = api_post(
                    "/patients/upload/pdf",
                    files={"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")},
                )
                if resp.status_code == 201:
                    st.success(f"Created patient #{resp.json()['id']}")
                else:
                    st.error(f"{resp.status_code}: {resp.text}")

    patients = api_get("/patients", limit=200)
    if not patients:
        st.info("No patients yet. Upload a CSV or generate synthetic data.")
        return

    st.dataframe(patients, use_container_width=True)


def patient_detail_page() -> None:
    st.header("Patient detail")
    patients = api_get("/patients", limit=200)
    if not patients:
        st.info("No patients yet.")
        return

    options = {f"#{p['id']} {p.get('name') or ''}".strip(): p["id"] for p in patients}
    label = st.selectbox("Select a patient", list(options.keys()))
    pid = options[label]

    detail = api_get(f"/patients/{pid}")
    st.subheader("Demographics")
    st.json({k: detail[k] for k in ("id", "external_id", "name", "sex", "age", "height_cm", "weight_kg")})

    st.subheader("Labs")
    st.dataframe(detail["labs"] or [], use_container_width=True)
    st.subheader("Vitals")
    st.dataframe(detail["vitals"] or [], use_container_width=True)

    st.subheader("Diabetes risk")
    if st.button("Compute risk"):
        risk = api_get(f"/patients/{pid}/risk")
        level = risk["risk_level"]
        st.metric("Risk level", level.upper(), f"{round(risk['probability'] * 100)}%")
        st.caption(f"Model source: {risk['model_source']} | condition: {risk['condition']}")
        st.write("Top contributing features:")
        st.dataframe(risk["contributions"], use_container_width=True)


def chat_page() -> None:
    st.header("Chat with the health agent")
    patients = api_get("/patients", limit=200)
    if not patients:
        st.info("Create a patient first.")
        return

    options = {f"#{p['id']} {p.get('name') or ''}".strip(): p["id"] for p in patients}
    label = st.selectbox("Patient", list(options.keys()))
    pid = options[label]

    message = st.text_input("Ask about this patient's data", "What does my LDL mean?")
    if st.button("Send"):
        resp = api_post("/chat", json={"patient_id": pid, "message": message})
        if resp.status_code != 200:
            st.error(f"{resp.status_code}: {resp.text}")
            return
        body = resp.json()
        st.markdown(body["answer"])
        if body["citations"]:
            st.subheader("Citations")
            for c in body["citations"]:
                st.markdown(f"- **{c['source']}** (score {c['score']}): {c['excerpt']}")
        with st.expander("Tool calls"):
            st.json(body["tool_calls"])


def knowledge_page() -> None:
    st.header("Medical knowledge base")
    query = st.text_input("Search or ask", "What does elevated LDL mean?")
    mode = st.radio("Mode", ["Ask", "Search"], horizontal=True)
    if st.button("Go"):
        if mode == "Ask":
            body = api_get("/knowledge/ask", q=query)
            st.markdown(body["answer"])
            for c in body["citations"]:
                st.markdown(f"- **{c['source']}**: {c['excerpt']}")
        else:
            hits = api_get("/knowledge/search", q=query, top_k=5)
            for h in hits:
                st.markdown(f"**{h['source']}** (score {h['score']})")
                st.caption(h["text"])


PAGES = {
    "Patients": patients_page,
    "Patient detail": patient_detail_page,
    "Chat": chat_page,
    "Knowledge": knowledge_page,
}


def main() -> None:
    st.title("AI Personalized Medicine")
    st.caption("Educational Python project — not for clinical use")

    ok, status = check_api()
    if ok:
        st.sidebar.success(f"API: {status} ({API_BASE_URL})")
    else:
        st.sidebar.error(f"API unreachable at {API_BASE_URL}")
        st.warning(
            "Start the backend: `uvicorn backend.api.main:app --reload`, "
            "then reload this page."
        )

    choice = st.sidebar.radio("Page", list(PAGES.keys()))
    PAGES[choice]()


if __name__ == "__main__":
    main()
else:
    main()
