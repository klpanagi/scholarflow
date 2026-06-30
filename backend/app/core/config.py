"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, Field
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        case_sensitive=True,
    )
    
    # Application
    APP_NAME: str = "ScholarFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://user:pass@localhost:5432/academicpal"
    
    # Redis
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_PAPERS_INDEX: str = "assets"
    ELASTICSEARCH_CHUNKS_INDEX: str = "chunks"
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_PAPERS: str = "assets"
    MINIO_BUCKET_DRAFTS: str = "drafts"
    MINIO_BUCKET_REVIEWS: str = "reviews"
    
    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    
    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # LLM Providers
    OPENAI_API_KEY: str = ""
    OPENCODE_GO_API_KEY: str = ""
    OPENCODE_GO_API_BASE: str = "https://opencode.ai/zen/go/v1"
    OPENCODE_ZEN_API_KEY: str = ""
    OPENCODE_ZEN_API_BASE: str = "https://opencode.ai/zen/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_API_BASE: str = "https://openrouter.ai/api/v1"
    LITELLM_MASTER_KEY: str = ""
    
    # ARQ Task Queue
    ARQ_REDIS_URL: RedisDsn = "redis://localhost:6379/1"  # DB 1 (repurposed from Celery)
    ARQ_JOB_TIMEOUT_ASSET: int = 600       # 10 minutes
    ARQ_JOB_TIMEOUT_WORKFLOW: int = 3600   # 1 hour
    ARQ_KEEP_RESULT_SECONDS: int = 86400   # 7 days
    ARQ_MAX_RETRIES_ASSET: int = 3
    ARQ_MAX_RETRIES_WORKFLOW: int = 2
    ARQ_CONCURRENCY_ASSET: int = 2
    ARQ_CONCURRENCY_WORKFLOW: int = 4
    
    # External Services
    GROBID_URL: str = "http://localhost:8070"
    TIKA_URL: str = "http://localhost:9998"
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    CROSSREF_API_KEY: str = ""


settings = Settings()
