from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BPM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("ALLOWED_SCHEMA_VERSIONS", "1.1")
os.environ.setdefault("ALLOWED_FORMULA_VERSIONS", "bpm-3.0.1")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.db_models import Base

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
_TestSessionLocal = async_sessionmaker(bind=_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with _TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def valid_payload() -> dict:
    return {
        "webhook_secret": "test-secret", "schema_version": "1.1", "formula_version": "bpm-3.0.1",
        "configuration_id": "BPM-DEFAULT-CONF-01", "event_id": "TEST:EVENT:0001", "symbol": "BTCUSD",
        "exchange": "COINBASE", "timeframe": "5", "bpm_mode": "Structural",
        "bar_open_time": 1000, "bar_close_time": 2000, "confirmed_state": "Expansion",
        "confirmed_direction": "Bullish", "bo_status": "Confirmed", "active_bo_price": 100.5,
        "mc_status": "Provisional", "active_mc_price": 110.25, "pressure_efficiency": 62.5,
        "acceptance_status": "Moderate", "bes_scenario": "BES-2 Momentum (MCZ-RZ)",
    }
