from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/personalized_medicine"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    # Embedding backend selection: "auto" | "sentence_transformers" | "openai" | "local".
    # "auto" prefers a local semantic model when installed, then OpenAI, then the
    # dependency-free lexical embedder.
    embedding_backend: str = "auto"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
