"""Real BehavioralDataProvider reading the latest confirmed Pine
telemetry event for a symbol from telemetry_events (the same table the
webhook route writes to). This is the concrete bridge from "TradingView
is the behavioral sensor" to "Python is the brain" — it never
recomputes BO/MC/state, only reads Pine's own confirmed output.

Verification status: syntax-checked only — no live database here.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TelemetryEvent
from app.models.snapshot import BehavioralData
from app.providers.base import BehavioralDataProvider


class DatabaseBehavioralDataProvider(BehavioralDataProvider):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_behavioral_data(self, symbol: str) -> Optional[BehavioralData]:
        stmt = (
            select(TelemetryEvent)
            .where(TelemetryEvent.symbol == symbol)
            .order_by(TelemetryEvent.received_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()
        if event is None:
            return None
        return BehavioralData(
            confirmed_state=event.confirmed_state,
            confirmed_direction=event.confirmed_direction,
            bo_status=event.bo_status,
            mc_status=event.mc_status,
            pressure_efficiency=event.pressure_efficiency,
            acceptance_status=event.acceptance_status,
            bes_scenario=event.bes_scenario,
            active_bo_price=event.active_bo_price,
            active_mc_price=event.active_mc_price,
            # forecast_bias / bars_in_confirmed_state / recent_transition_count
            # are not part of Pine's current telemetry payload — a real
            # deployment would join against BehavioralSnapshot/BehavioralTransition
            # history in the Behavioral Database to populate these.
        )
