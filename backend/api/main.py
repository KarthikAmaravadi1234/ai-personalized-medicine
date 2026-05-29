from fastapi import FastAPI

app = FastAPI(
    title="AI Personalized Medicine",
    description="Educational Python API for personalized healthcare insights",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Personalized Medicine API", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
