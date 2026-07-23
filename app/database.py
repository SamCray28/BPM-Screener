"""Async SQLAlchemy engine/session wiring. Postgres in production via
DATABASE_URL using an async driver (postgresql+asyncpg://...); SQLite
(via aiosqlite) is the local/test-only fallback — never assumed live.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, future=True)

AsyncSessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
