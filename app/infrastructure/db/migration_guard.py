"""Database migration safety guards and remote Supabase interlock."""

import os
import sys

from app.core.config import settings


def check_remote_migration_safety() -> None:
    """원격 Supabase/클라우드 DB 대상 실수로 인한 마이그레이션 실행을 차단하는 안전 인터락.

    로컬 개발 중 ALLOW_REMOTE_MIGRATION=true 환경변수 없이 원격 DB(pooler.supabase.com 등)에
    마이그레이션 DDL이 실행되는 것을 원천 차단합니다.
    """
    allow_remote = (
        os.getenv("ALLOW_REMOTE_MIGRATION", "").lower() in ("true", "1", "yes")
        or settings.allow_remote_migration
    )

    if settings.is_remote_db and not allow_remote:
        target_host = settings.db_host or "remote-host"
        error_msg = (
            f"\n[MIGRATION BLOCKED] 안전 인터락 발동: 현재 대상 데이터베이스는 원격 호스트({target_host})입니다.\n"
            f"로컬 개발 환경에서 팀 공용 DB에 실수로 마이그레이션이 적용되는 것을 방지하기 위해 차단되었습니다.\n"
            f"팀원들과 협의 후 원격 DB에 실제로 마이그레이션을 적용하려면 아래와 같이 실행하십시오:\n\n"
            f"  ALLOW_REMOTE_MIGRATION=true alembic upgrade head\n"
            f"  (또는 ALLOW_REMOTE_MIGRATION=true uv run python scripts/run_migrations.py upgrade)\n"
        )
        print(error_msg, file=sys.stderr)
        raise RuntimeError(
            f"Remote database migration blocked for host '{target_host}'. "
            "Set ALLOW_REMOTE_MIGRATION=true to proceed."
        )
