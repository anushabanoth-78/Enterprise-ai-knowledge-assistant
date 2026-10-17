from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rag:rag@db:5432/rag"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"

    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 50

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_words: int = 220
    chunk_overlap: int = 40

    hosted_base_url: str = "https://api.openai.com/v1"
    hosted_api_key: str = ""
    hosted_model: str = "gpt-4o-mini"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    llm_timeout_s: float = 60.0

    rate_limit_per_minute: int = 60


settings = Settings()
