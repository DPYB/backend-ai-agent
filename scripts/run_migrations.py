"""Alembic and database schema migration helper script.

Usage:
    uv run python scripts/run_migrations.py upgrade
    uv run python scripts/run_migrations.py downgrade
    uv run python scripts/run_migrations.py current
"""

import argparse
import sys

from alembic.config import Config

from alembic import command
from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Alembic database migrations for agent schema")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade", "current", "history"],
        help="Migration action to perform",
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="Target revision (default: 'head' for upgrade, '-1' for downgrade)",
    )
    args = parser.parse_args()

    if not settings.is_db_configured:
        print("Error: Database connection is not configured in .env!", file=sys.stderr)
        sys.exit(1)

    alembic_cfg = Config("alembic.ini")

    if args.action == "upgrade":
        print(f"Applying migrations up to revision '{args.revision}' on schema 'agent'...")
        command.upgrade(alembic_cfg, args.revision)
        print("Migrations applied successfully!")
    elif args.action == "downgrade":
        target = args.revision if args.revision != "head" else "-1"
        print(f"Downgrading migrations down to '{target}' on schema 'agent'...")
        command.downgrade(alembic_cfg, target)
        print("Downgrade completed successfully!")
    elif args.action == "current":
        command.current(alembic_cfg)
    elif args.action == "history":
        command.history(alembic_cfg)


if __name__ == "__main__":
    main()
