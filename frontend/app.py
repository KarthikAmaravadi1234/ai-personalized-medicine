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

st.set_page_config(
    page_title="AI Personalized Medicine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }

        /* App background: soft gradient wash */
        .stApp {
            background:
                radial-gradient(1200px 600px at 100% -10%, rgba(99,102,241,0.08), transparent 60%),
                radial-gradient(1000px 500px at -10% 10%, rgba(6,182,212,0.08), transparent 55%),
                #f7f8fc;
        }

        /* Trim default top padding */
        .block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1200px; }

        /* Hero banner */
        .hero {
            border-radius: 22px;
            padding: 34px 38px;
            background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 45%, #06b6d4 100%);
            color: #fff;
            box-shadow: 0 18px 40px -16px rgba(79,70,229,0.55);
            position: relative;
            overflow: hidden;
        }
        .hero::after {
            content: "";
            position: absolute; right: -60px; top: -60px;
            width: 240px; height: 240px; border-radius: 50%;
            background: rgba(255,255,255,0.12);
        }
        .hero h1 { font-size: 2.1rem; font-weight: 800; margin: 0 0 6px 0; letter-spacing: -0.5px; }
        .hero p { font-size: 1.02rem; opacity: 0.92; margin: 0; max-width: 720px; }
        .hero .tagpills { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
        .hero .tagpill {
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.28);
            padding: 5px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600;
            backdrop-filter: blur(4px);
        }

        /* KPI / content cards */
        .card {
            background: #ffffff;
            border: 1px solid #eef0f6;
            border-radius: 18px;
            padding: 20px 22px;
            box-shadow: 0 10px 30px -18px rgba(15,23,42,0.25);
            height: 100%;
        }
        .kpi-label { font-size: 0.82rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.6px; }
        .kpi-value { font-size: 2rem; font-weight: 800; color: #0f172a; line-height: 1.1; margin-top: 6px; }
        .kpi-sub { font-size: 0.84rem; color: #94a3b8; margin-top: 2px; }
        .kpi-accent { width: 42px; height: 42px; border-radius: 12px; display:flex; align-items:center; justify-content:center; font-size: 1.3rem; margin-bottom: 10px; }

        .section-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin: 8px 0 4px 0; }
        .section-sub { color: #64748b; font-size: 0.92rem; margin-bottom: 14px; }

        /* Pills */
        .pill { display:inline-flex; align-items:center; gap:6px; padding: 5px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 700; }
        .pill-green { background: #dcfce7; color: #15803d; }
        .pill-amber { background: #fef3c7; color: #b45309; }
        .pill-red   { background: #fee2e2; color: #b91c1c; }
        .pill-blue  { background: #e0e7ff; color: #4338ca; }
        .pill-slate { background: #e2e8f0; color: #475569; }

        /* Buttons: gradient primary */
        .stButton > button {
            border-radius: 12px;
            border: none;
            padding: 0.55rem 1.1rem;
            font-weight: 600;
            background: linear-gradient(120deg, #4f46e5, #7c3aed);
            color: #fff;
            transition: transform .08s ease, box-shadow .2s ease;
            box-shadow: 0 8px 20px -10px rgba(79,70,229,0.7);
        }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 12px 24px -10px rgba(79,70,229,0.8); color:#fff; }
        .stButton > button:active { transform: translateY(0); }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
        }
        [data-testid="stSidebar"] * { color: #e2e8f0; }
        [data-testid="stSidebar"] .brand {
            font-size: 1.25rem; font-weight: 800; color: #fff; letter-spacing: -0.3px;
            display:flex; align-items:center; gap:10px; margin-bottom: 2px;
        }
        [data-testid="stSidebar"] .brand-sub { color: #a5b4fc; font-size: 0.8rem; margin-bottom: 18px; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label { color: #e2e8f0 !important; }

        /* Metric tweaks */
        [data-testid="stMetricValue"] { font-weight: 800; }

        /* Dataframe rounding */
        [data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }

        /* Hide default footer/menu chrome */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# API helpers
# --------------------------------------------------------------------------- #
def api_get(path: str, **params):
    resp = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, json=None, files=None):
    return httpx.post(f"{API_BASE_URL}{path}", json=json, files=files, timeout=TIMEOUT)


def get_health() -> dict | None:
    try:
        return api_get("/health")
    except Exception:  # noqa: BLE001
        return None


def safe_patients() -> list[dict]:
    try:
        return api_get("/patients", limit=200)
    except Exception:  # noqa: BLE001
        return []


# --------------------------------------------------------------------------- #
# UI building blocks
# --------------------------------------------------------------------------- #
def hero(title: str, subtitle: str, tags: list[str]) -> None:
    pills = "".join(f'<span class="tagpill">{t}</span>' for t in tags)
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            <div class="tagpills">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str, icon: str, bg: str) -> str:
    return f"""
        <div class="card">
            <div class="kpi-accent" style="background:{bg};">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    """


def section(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="section-sub">{sub}</div>', unsafe_allow_html=True)


def pill(text: str, kind: str) -> str:
    return f'<span class="pill pill-{kind}">{text}</span>'


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def dashboard_page() -> None:
    hero(
        "AI Personalized Medicine",
        "An educational platform that turns labs, vitals, and clinical knowledge into "
        "personalized, grounded health insights — with an AI agent that always cites its sources.",
        ["RAG knowledge base", "ML risk scoring", "Guardrailed AI agent"],
    )
    st.write("")

    patients = safe_patients()
    total = len(patients)
    ages = [p.get("age") for p in patients if p.get("age")]
    avg_age = round(sum(ages) / len(ages)) if ages else 0
    males = sum(1 for p in patients if str(p.get("sex", "")).lower() == "male")
    females = sum(1 for p in patients if str(p.get("sex", "")).lower() == "female")

    health = get_health()
    llm_mode = (health or {}).get("llm_mode", "unknown")
    llm_text = {"openai": "OpenAI", "local_fallback": "Local (fallback)", "local": "Local"}.get(
        llm_mode, "Unknown"
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            kpi_card("Patients", str(total), "in the database", "👥", "#e0e7ff"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            kpi_card("Average age", str(avg_age) if avg_age else "—", "years", "📈", "#dcfce7"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            kpi_card("Cohort", f"{males} / {females}", "male / female", "⚖️", "#fef3c7"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            kpi_card("AI engine", llm_text, "active inference mode", "🤖", "#cffafe"),
            unsafe_allow_html=True,
        )

    st.write("")
    section("Recent patients", "The latest records ingested into the platform.")
    if patients:
        st.dataframe(patients[-8:][::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No patients yet. Head to **Patients** to upload a CSV or PDF lab report.")


def patients_page() -> None:
    section("Patients", "Upload patient data and browse the cohort.")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**📄 Upload a patient CSV**")
            csv_file = st.file_uploader("CSV of patients", type=["csv"], key="csv", label_visibility="collapsed")
            if csv_file and st.button("Upload CSV", key="btn_csv"):
                resp = api_post(
                    "/patients/upload",
                    files={"file": (csv_file.name, csv_file.getvalue(), "text/csv")},
                )
                if resp.status_code == 201:
                    st.success(f"Uploaded: {resp.json()}")
                else:
                    st.error(f"{resp.status_code}: {resp.text}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**🧾 Upload a PDF lab report**")
            pdf_file = st.file_uploader("PDF lab report", type=["pdf"], key="pdf", label_visibility="collapsed")
            if pdf_file and st.button("Upload PDF", key="btn_pdf"):
                resp = api_post(
                    "/patients/upload/pdf",
                    files={"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")},
                )
                if resp.status_code == 201:
                    st.success(f"Created patient #{resp.json()['id']}")
                else:
                    st.error(f"{resp.status_code}: {resp.text}")
            st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    patients = safe_patients()
    if not patients:
        st.info("No patients yet. Upload a CSV/PDF above or generate synthetic data.")
        return
    section("Cohort")
    st.dataframe(patients, use_container_width=True, hide_index=True)


def _patient_selector(patients: list[dict], key: str) -> int:
    options = {f"#{p['id']} · {p.get('name') or 'Unnamed'}": p["id"] for p in patients}
    label = st.selectbox("Select a patient", list(options.keys()), key=key)
    return options[label]


def patient_detail_page() -> None:
    section("Patient detail", "Demographics, labs, vitals, and an ML diabetes-risk estimate.")
    patients = safe_patients()
    if not patients:
        st.info("No patients yet.")
        return

    pid = _patient_selector(patients, key="detail_sel")
    detail = api_get(f"/patients/{pid}")

    demo = {k: detail.get(k) for k in ("id", "external_id", "name", "sex", "age", "height_cm", "weight_kg")}
    cols = st.columns(4)
    fields = [
        ("Name", demo.get("name") or "—"),
        ("Age", demo.get("age") or "—"),
        ("Sex", (demo.get("sex") or "—")),
        ("ID", f"#{demo.get('id')}"),
    ]
    for col, (lbl, val) in zip(cols, fields):
        with col:
            st.markdown(
                kpi_card(lbl, str(val), "", "🩺", "#eef2ff"),
                unsafe_allow_html=True,
            )

    st.write("")
    left, right = st.columns(2)
    with left:
        section("Labs")
        st.dataframe(detail.get("labs") or [], use_container_width=True, hide_index=True)
    with right:
        section("Vitals")
        st.dataframe(detail.get("vitals") or [], use_container_width=True, hide_index=True)

    st.write("")
    section("Diabetes risk", "A statistical estimate from an educational model — not a diagnosis.")
    if st.button("Compute risk", key="btn_risk"):
        risk = api_get(f"/patients/{pid}/risk")
        level = str(risk["risk_level"]).lower()
        kind = {"high": "red", "moderate": "amber", "low": "green"}.get(level, "slate")
        m1, m2 = st.columns([1, 2])
        with m1:
            st.markdown(
                f'<div class="card"><div class="kpi-label">Risk level</div>'
                f'<div style="margin-top:10px">{pill(level.upper(), kind)}</div>'
                f'<div class="kpi-value">{round(risk["probability"] * 100)}%</div>'
                f'<div class="kpi-sub">{risk["condition"]} · {risk["model_source"]}</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**Top contributing features**")
            st.dataframe(risk["contributions"], use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)


def chat_page() -> None:
    section("Health agent", "Ask about a patient's data. The agent uses tools, cites sources, and applies safety guardrails.")
    patients = safe_patients()
    if not patients:
        st.info("Create a patient first.")
        return

    pid = _patient_selector(patients, key="chat_sel")

    history_key = f"chat_history_{pid}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    for turn in st.session_state[history_key]:
        with st.chat_message(turn["role"], avatar="🧑" if turn["role"] == "user" else "🧬"):
            st.markdown(turn["content"])
            if turn.get("citations"):
                with st.expander("Sources"):
                    for c in turn["citations"]:
                        st.markdown(f"- **{c['source']}** (score {c['score']}): {c['excerpt']}")

    prompt = st.chat_input("Ask about this patient's data…")
    if prompt:
        st.session_state[history_key].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🧬"):
            with st.spinner("Thinking…"):
                resp = api_post("/chat", json={"patient_id": pid, "message": prompt})
            if resp.status_code != 200:
                st.error(f"{resp.status_code}: {resp.text}")
                return
            body = resp.json()
            st.markdown(body["answer"])
            if body.get("citations"):
                with st.expander("Sources"):
                    for c in body["citations"]:
                        st.markdown(f"- **{c['source']}** (score {c['score']}): {c['excerpt']}")
            if body.get("tool_calls"):
                with st.expander("Tool calls"):
                    st.json(body["tool_calls"])
        st.session_state[history_key].append(
            {"role": "assistant", "content": body["answer"], "citations": body.get("citations", [])}
        )


def knowledge_page() -> None:
    section("Medical knowledge base", "Retrieval-augmented answers and semantic search over the curated library.")
    query = st.text_input("Search or ask a question", "What does elevated LDL mean?")
    mode = st.radio("Mode", ["Ask", "Search"], horizontal=True, label_visibility="collapsed")
    if st.button("Go", key="btn_kb"):
        if mode == "Ask":
            body = api_get("/knowledge/ask", q=query)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(body["answer"])
            st.markdown("</div>", unsafe_allow_html=True)
            if body.get("citations"):
                section("Citations")
                for c in body["citations"]:
                    st.markdown(f"- **{c['source']}**: {c['excerpt']}")
        else:
            hits = api_get("/knowledge/search", q=query, top_k=5)
            for h in hits:
                source = h["source"]
                score_pill = pill(f"score {h['score']}", "blue")
                text = h["text"]
                st.markdown(
                    f'<div class="card" style="margin-bottom:12px">'
                    f"<b>{source}</b> &nbsp; {score_pill}"
                    f'<div class="kpi-sub" style="margin-top:8px">{text}</div></div>',
                    unsafe_allow_html=True,
                )


PAGES = {
    "📊  Dashboard": dashboard_page,
    "👥  Patients": patients_page,
    "🩺  Patient detail": patient_detail_page,
    "💬  Chat": chat_page,
    "📚  Knowledge": knowledge_page,
}


def sidebar() -> str:
    st.sidebar.markdown('<div class="brand">🧬 MediMind AI</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="brand-sub">Personalized medicine, grounded in evidence</div>', unsafe_allow_html=True)

    choice = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

    st.sidebar.markdown("---")
    health = get_health()
    if health is None:
        st.sidebar.markdown(pill("● API offline", "red"), unsafe_allow_html=True)
        st.sidebar.caption(f"No backend at {API_BASE_URL}")
    else:
        status = health.get("status", "unknown")
        status_kind = "green" if status == "healthy" else "amber"
        st.sidebar.markdown(pill(f"● API {status}", status_kind), unsafe_allow_html=True)
        llm_mode = health.get("llm_mode", "unknown")
        llm_kind = {"openai": "blue", "local_fallback": "amber", "local": "slate"}.get(llm_mode, "slate")
        llm_text = {
            "openai": "AI: OpenAI",
            "local_fallback": "AI: Local fallback",
            "local": "AI: Local",
        }.get(llm_mode, "AI: Unknown")
        st.sidebar.markdown(pill(llm_text, llm_kind), unsafe_allow_html=True)
        cooldown = (health.get("openai") or {}).get("cooldown_remaining_s", 0)
        if llm_mode == "local_fallback" and cooldown:
            st.sidebar.caption(f"OpenAI retry in ~{int(cooldown)}s")

    st.sidebar.markdown("---")
    st.sidebar.caption("Educational project — not for clinical use.")
    return choice


def main() -> None:
    inject_css()
    choice = sidebar()

    if get_health() is None:
        st.warning(
            "Backend unreachable. Start it with "
            "`uvicorn backend.api.main:app --reload`, then reload this page."
        )

    PAGES[choice]()


main()
