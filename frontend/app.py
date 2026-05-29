import streamlit as st

st.set_page_config(page_title="AI Personalized Medicine", page_icon="🧬", layout="wide")

st.title("AI Personalized Medicine")
st.caption("Educational Python project — not for clinical use")

st.info(
    "Streamlit UI scaffold. Connect to the FastAPI backend in Phase 5, "
    "or start the API with: `uv run uvicorn backend.api.main:app --reload`"
)

st.markdown("---")
st.subheader("Quick links")
st.markdown("- [API docs](http://localhost:8000/docs)")
st.markdown("- [Health check](http://localhost:8000/health)")
