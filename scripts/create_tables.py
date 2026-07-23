"""Fallback table creation via Base.metadata.create_all(), for quick
local setup without running Alembic. For any real deployment, prefer
`alembic upgrade head` instead — this script does not track schema
versions or support downgrades.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python scripts/create_tables.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models.db_models import Base


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("BPM tables created (or already present).")


if __name__ == "__main__":
    asyncio.run(main())
