"""Global pytest configuration and fixtures for backend-ai-agent."""

import os

import pytest

# Ensure APP_ENV is set to test during pytest runs to enable fast mock bypass
os.environ["APP_ENV"] = "test"

from app.core.config import settings

settings.app_env = "test"


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch):
    """Automatically set APP_ENV=test for all unit tests."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(settings, "app_env", "test")
