import sys
from pathlib import Path

# Allow running this file directly (python backend/api/main.py) by putting the
# project root on sys.path so the top-level `backend` package is importable.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes import chat, knowledge, patients
from backend.db.engine import check_connection
from backend.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database tables initialized.")
    except Exception as exc:  # keep the app bootable even if the DB is down in dev
        logger.warning("Skipping DB initialization (database unavailable): %s", exc)
    yield


app = FastAPI(
    title="AI Personalized Medicine",
    description="Educational Python API for personalized healthcare insights",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(patients.router)
app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Personalized Medicine API", "status": "ok"}


@app.get("/health")
def health() -> dict[str, object]:
    from backend.config import get_settings
    from backend.llm import get_circuit

    db_ok = check_connection()
    settings = get_settings()
    circuit = get_circuit()
    if not settings.openai_api_key:
        llm_mode = "local"  # no key configured
    elif circuit.is_available():
        llm_mode = "openai"
    else:
        llm_mode = "local_fallback"  # key set but OpenAI temporarily disabled
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "llm_mode": llm_mode,
        "openai": circuit.status(),
    }


if __name__ == "__main__":
    import uvicorn

    from backend.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
