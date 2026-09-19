"""Unit tests for configuration validation and security guards."""

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings


def test_settings_development_allows_default_jwt_secret() -> None:
    """Verify that development/test environments allow default JWT secret."""
    settings = Settings(
        APP_ENV="development",
        JWT_SECRET_KEY=DEFAULT_JWT_SECRET,
    )
    assert settings.jwt_secret_key == DEFAULT_JWT_SECRET
    assert settings.app_env == "development"


def test_settings_production_blocks_default_jwt_secret() -> None:
    """Verify that production environment raises error if default JWT secret is used."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY=DEFAULT_JWT_SECRET,
        )
    assert "기본 JWT_SECRET_KEY를 사용할 수 없습니다" in str(exc_info.value)


def test_settings_production_blocks_empty_jwt_secret() -> None:
    """Verify that production environment raises error if JWT secret is empty."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="   ",
        )
    assert "기본 JWT_SECRET_KEY를 사용할 수 없습니다" in str(exc_info.value)


def test_settings_production_allows_strong_custom_jwt_secret() -> None:
    """Verify that production environment starts normally with strong custom JWT secret."""
    settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="my-super-secret-secure-jwt-key-for-2026-prod",
    )
    assert settings.jwt_secret_key == "my-super-secret-secure-jwt-key-for-2026-prod"
    assert settings.app_env == "production"


def test_is_remote_db_detection() -> None:
    """Verify remote DB detection logic."""
    local_settings = Settings(DB_HOST="localhost")
    assert local_settings.is_remote_db is False

    local_ip_settings = Settings(DB_HOST="127.0.0.1")
    assert local_ip_settings.is_remote_db is False

    supabase_settings = Settings(DB_HOST="aws-0-ap-northeast-2.pooler.supabase.com")
    assert supabase_settings.is_remote_db is True

    url_supabase = Settings(
        DATABASE_URL="postgresql+asyncpg://postgres:pass@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"
    )
    assert url_supabase.is_remote_db is True
