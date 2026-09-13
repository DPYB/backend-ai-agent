"""Application settings and environment configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for DPYB backend-ai-agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    # Google Gemini AI (Primary Free Tier)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.8-flash", alias="GEMINI_MODEL")
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        alias="GEMINI_EMBEDDING_MODEL",
    )

    # OpenAI API (Fallback / Alternative LLM)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Supabase pgvector (Cloud Free Tier)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")

    # Redis (Session State & Cache)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl_seconds: int = Field(default=3600, alias="REDIS_CACHE_TTL_SECONDS")

    # Tavily Web Search (Free Tier)
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # backend-core-api REST Endpoint
    core_api_base_url: str = Field(default="http://localhost:8080", alias="CORE_API_BASE_URL")
    core_api_timeout_seconds: float = Field(default=5.0, alias="CORE_API_TIMEOUT_SECONDS")

    # NAVER Cloud CLOVA OCR General API V2
    naver_clova_api_url: str = Field(default="", alias="NAVER_CLOVA_API_URL")
    naver_clova_secret_key: str = Field(default="", alias="NAVER_CLOVA_SECRET_KEY")

    @property
    def cors_origin_list(self) -> List[str]:
        """Return parsed list of CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_testing(self) -> bool:
        """Check if environment is testing."""
        return self.app_env.lower() in ("test", "testing")


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton instance."""
    return Settings()


settings = get_settings()
