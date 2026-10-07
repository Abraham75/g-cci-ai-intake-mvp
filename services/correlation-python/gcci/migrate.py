from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import asyncpg

from .config import settings


MIGRATION_LOCK_KEY = 874222


def _asyncpg_dsn() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _migration_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[1] / "migrations",
        Path.cwd() / "migrations",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError("Migration directory not found")


async def migrate() -> None:
    directory = _migration_dir()
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise RuntimeError(f"No migrations found in {directory}")

    connection = await asyncpg.connect(_asyncpg_dsn())
    try:
        await connection.execute("SELECT pg_advisory_lock($1)", MIGRATION_LOCK_KEY)
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name text PRIMARY KEY,
                sha256 varchar(64) NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )

        applied = {
            row["migration_name"]: row["sha256"]
            for row in await connection.fetch(
                "SELECT migration_name, sha256 FROM schema_migrations"
            )
        }

        for path in files:
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            existing = applied.get(path.name)
            if existing:
                if existing != digest:
                    raise RuntimeError(
                        f"Applied migration {path.name} was modified after deployment; "
                        "create a new migration instead of editing history."
                    )
                continue

            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations(migration_name, sha256) VALUES($1, $2)",
                    path.name,
                    digest,
                )
            print(f"applied migration {path.name}", flush=True)
    finally:
        try:
            await connection.execute("SELECT pg_advisory_unlock($1)", MIGRATION_LOCK_KEY)
        finally:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(migrate())
