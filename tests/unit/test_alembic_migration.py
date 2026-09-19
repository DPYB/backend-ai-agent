"""Unit tests for Alembic configuration and migration script integrity."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_ini_exists_and_parses() -> None:
    """Verify that alembic.ini exists and script_location is configured correctly."""
    repo_root = Path(__file__).parent.parent.parent
    ini_path = repo_root / "alembic.ini"
    assert ini_path.exists(), "alembic.ini should exist in repo root"

    cfg = Config(str(ini_path))
    script_loc = cfg.get_main_option("script_location")
    assert script_loc is not None
    assert "alembic" in script_loc


def test_alembic_script_directory_and_revisions() -> None:
    """Verify that the Alembic migration history has valid revisions."""
    repo_root = Path(__file__).parent.parent.parent
    ini_path = repo_root / "alembic.ini"
    cfg = Config(str(ini_path))

    script_dir = ScriptDirectory.from_config(cfg)
    heads = script_dir.get_heads()
    assert len(heads) == 1, "There should be exactly one current head revision"
    assert heads[0] == "001_initial_agent_schema"

    rev_001 = script_dir.get_revision("001_initial_agent_schema")
    assert rev_001 is not None
    assert rev_001.down_revision is None
    assert hasattr(rev_001.module, "upgrade")
    assert hasattr(rev_001.module, "downgrade")


def test_alembic_env_schema_target() -> None:
    """Verify that alembic/env.py configures version_table_schema as 'agent'."""
    repo_root = Path(__file__).parent.parent.parent
    env_py_path = repo_root / "alembic" / "env.py"
    assert env_py_path.exists()

    content = env_py_path.read_text(encoding="utf-8")
    assert 'version_table_schema="agent"' in content
    assert "CREATE SCHEMA IF NOT EXISTS agent;" in content
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in content
    assert "statement_cache_size" in content
    assert "check_remote_migration_safety" in content


def test_remote_migration_guard_blocks_remote_host(monkeypatch) -> None:
    """Verify that remote DB migration raises RuntimeError when ALLOW_REMOTE_MIGRATION is False."""
    import pytest

    from app.core.config import settings
    from app.infrastructure.db.migration_guard import check_remote_migration_safety

    monkeypatch.setattr(settings, "db_host", "aws-0-ap-northeast-2.pooler.supabase.com")
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "allow_remote_migration", False)
    monkeypatch.delenv("ALLOW_REMOTE_MIGRATION", raising=False)

    assert settings.is_remote_db is True

    with pytest.raises(RuntimeError, match="Remote database migration blocked"):
        check_remote_migration_safety()


def test_remote_migration_guard_allows_when_flag_set(monkeypatch) -> None:
    """Verify that remote DB migration passes when ALLOW_REMOTE_MIGRATION is True."""
    from app.core.config import settings
    from app.infrastructure.db.migration_guard import check_remote_migration_safety

    monkeypatch.setattr(settings, "db_host", "aws-0-ap-northeast-2.pooler.supabase.com")
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "allow_remote_migration", True)

    assert settings.is_remote_db is True
    # Should not raise
    check_remote_migration_safety()


def test_remote_migration_guard_allows_local_db(monkeypatch) -> None:
    """Verify that local database migration passes without any special flag."""
    from app.core.config import settings
    from app.infrastructure.db.migration_guard import check_remote_migration_safety

    monkeypatch.setattr(settings, "db_host", "localhost")
    monkeypatch.setattr(settings, "database_url", "")
    monkeypatch.setattr(settings, "allow_remote_migration", False)
    monkeypatch.delenv("ALLOW_REMOTE_MIGRATION", raising=False)

    assert settings.is_remote_db is False
    # Should not raise
    check_remote_migration_safety()
