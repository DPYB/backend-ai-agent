"""Application settings and environment configuration."""

from functools import lru_cache
from typing import List
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET: str = "dont-paw-get-jwt-secret-change-in-prod-2026"


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
    cors_origin_regex: str = Field(
        default=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        alias="CORS_ORIGIN_REGEX",
    )

    # Google Gemini AI (Smart Workload Routing & Multi-Key Free Tier)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_fallback_api_key: str = Field(default="", alias="GEMINI_FALLBACK_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", alias="GEMINI_MODEL")
    gemini_light_model: str = Field(default="gemini-3.1-flash-lite", alias="GEMINI_LIGHT_MODEL")
    gemma_emergency_model: str = Field(default="gemma-4-31b-it", alias="GEMMA_EMERGENCY_MODEL")
    gemini_embedding_model: str = Field(
        default="models/gemini-embedding-001",
        alias="GEMINI_EMBEDDING_MODEL",
    )
    gemini_embedding_dimension: int = Field(
        default=768,
        alias="GEMINI_EMBEDDING_DIMENSION",
    )

    # OpenAI API (Fallback / Alternative LLM)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Supabase pgvector (Cloud Free Tier - REST API)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")

    # Supabase PostgreSQL / Transaction Pooler (Multi-Schema & pgvector)
    db_user: str = Field(default="", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_host: str = Field(default="", alias="DB_HOST")
    db_port: int = Field(default=6543, alias="DB_PORT")
    db_name: str = Field(default="postgres", alias="DB_NAME")
    db_schema: str = Field(default="agent", alias="DB_SCHEMA")
    database_url: str = Field(default="", alias="DATABASE_URL")

    # Redis (Session State & Cache)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl_seconds: int = Field(default=3600, alias="REDIS_CACHE_TTL_SECONDS")

    # Tavily Web Search (Free Tier: 1,000 queries/month, $0 Zero-cost)
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    tavily_api_url: str = Field(
        default="https://api.tavily.com/search",
        alias="TAVILY_API_URL",
    )

    # National Library of Korea Open API (Aligned with backend-core-api NL_API_CERT_KEY)
    nl_api_cert_key: str = Field(default="", alias="NL_API_CERT_KEY")
    nl_api_search_url: str = Field(
        default="https://www.nl.go.kr/seoji/SearchApi.do",
        alias="NL_API_SEARCH_URL",
    )
    # Backward compatibility alias
    national_library_api_key: str = Field(default="", alias="NATIONAL_LIBRARY_API_KEY")
    national_library_api_url: str = Field(
        default="https://www.nl.go.kr/seoji/SearchApi.do",
        alias="NATIONAL_LIBRARY_API_URL",
    )

    # Google Books API (Supplementary Fallback for missing Page Count & Cover Image)
    google_books_api_key: str = Field(default="", alias="GOOGLE_BOOKS_API_KEY")
    google_books_api_url: str = Field(
        default="https://www.googleapis.com/books/v1/volumes",
        alias="GOOGLE_BOOKS_API_URL",
    )

    # backend-core-api REST Endpoint & Shared JWT Auth
    core_api_base_url: str = Field(default="http://localhost:8000", alias="CORE_API_BASE_URL")
    core_api_timeout_seconds: float = Field(default=5.0, alias="CORE_API_TIMEOUT_SECONDS")
    jwt_secret_key: str = Field(
        default="dont-paw-get-jwt-secret-change-in-prod-2026",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # NAVER Cloud CLOVA OCR General API V2
    naver_clova_api_url: str = Field(default="", alias="NAVER_CLOVA_API_URL")
    naver_clova_secret_key: str = Field(default="", alias="NAVER_CLOVA_SECRET_KEY")

    # Guest Mode Rate Limits & Role-based Circuit Breaker (70-80% safe buffer)
    guest_chat_limit: int = Field(default=10, alias="GUEST_CHAT_LIMIT")
    circuit_guest_rpm_limit: int = Field(default=60, alias="CIRCUIT_GUEST_RPM_LIMIT")
    circuit_guest_rpd_limit: int = Field(default=1400, alias="CIRCUIT_GUEST_RPD_LIMIT")
    circuit_member_rpm_limit: int = Field(default=120, alias="CIRCUIT_MEMBER_RPM_LIMIT")
    circuit_member_rpd_limit: int = Field(default=4000, alias="CIRCUIT_MEMBER_RPD_LIMIT")

    # Migration Safety Guard (Alembic Interlock for Remote Supabase DB)
    allow_remote_migration: bool = Field(default=False, alias="ALLOW_REMOTE_MIGRATION")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """운영 환경(production) 배포 시 기본 취약 시크릿 사용을 엄격히 차단 (Fail-Fast)."""
        env = (self.app_env or "").lower().strip()
        if env in ("production", "prod"):
            secret = (self.jwt_secret_key or "").strip()
            if not secret or secret == DEFAULT_JWT_SECRET:
                raise ValueError(
                    "[SECURITY ALERT] APP_ENV=production 환경에서는 기본 JWT_SECRET_KEY를 사용할 수 없습니다. "
                    "반드시 안전한 고유 시크릿 키를 환경변수에 설정하십시오."
                )
        return self

    @property
    def cors_origin_list(self) -> List[str]:
        """Return parsed list of CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_testing(self) -> bool:
        """Check if environment is testing."""
        return self.app_env.lower() in ("test", "testing")

    @property
    def is_remote_db(self) -> bool:
        """Check if target database host is a remote cloud instance (e.g. Supabase, RDS) rather than local."""
        host = (self.db_host or "").lower().strip()
        if not host:
            # If database_url is provided, check its host component
            if self.database_url:
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(self.database_url)
                    host = (parsed.hostname or "").lower().strip()
                except Exception:
                    host = ""
        return bool(host and host not in ("localhost", "127.0.0.1", "::1", "testserver"))

    @property
    def async_database_url(self) -> str:
        """Return asyncpg database connection URL with URL-encoded credentials."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        if self.db_host and self.db_user:
            encoded_password = quote_plus(self.db_password) if self.db_password else ""
            auth = f"{self.db_user}:{encoded_password}" if encoded_password else self.db_user
            return f"postgresql+asyncpg://{auth}@{self.db_host}:{self.db_port}/{self.db_name}"
        return ""

    @property
    def is_db_configured(self) -> bool:
        """Check if PostgreSQL/Supabase database connection is configured."""
        return bool(self.async_database_url)


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton instance."""
    return Settings()


settings = get_settings()
