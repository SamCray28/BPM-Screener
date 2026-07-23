"""Real HistoricalStatsProvider backed by the Behavioral Database
(app/models/db_models.py). This is what closes the loop the spec
describes: every completed trade updates win rate/profit factor/etc.,
and this provider is what turns those rows back into the HistoricalStats
shape every scoring engine already knows how to consume.

Verification status: syntax-checked only — no live database in this
sandbox to run these queries against.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import BehavioralSnapshot, TradeOutcome
from app.models.snapshot import HistoricalStats
from app.providers.base import HistoricalStatsProvider


async def get_stats_for_condition(session: AsyncSession, condition_key: str) -> HistoricalStats:
    stmt = (
        select(TradeOutcome)
        .join(BehavioralSnapshot, TradeOutcome.snapshot_id == BehavioralSnapshot.id)
        .where(BehavioralSnapshot.condition_key == condition_key)
        .where(TradeOutcome.r_multiple.is_not(None))
    )
    result = await session.execute(stmt)
    outcomes = list(result.scalars().all())
    occurrences = len(outcomes)
    if occurrences == 0:
        return HistoricalStats(occurrences=0)

    wins = [o for o in outcomes if o.is_win]
    r_values = [o.r_multiple for o in outcomes if o.r_multiple is not None]
    win_rate = len(wins) / occurrences if occurrences else None

    gross_profit = sum(r for r in r_values if r > 0)
    gross_loss = abs(sum(r for r in r_values if r < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    hold_bars = [o.hold_bars for o in outcomes if o.hold_bars is not None]
    mfe_values = [o.max_favorable_excursion for o in outcomes if o.max_favorable_excursion is not None]
    mae_values = [o.max_adverse_excursion for o in outcomes if o.max_adverse_excursion is not None]
    sorted_r = sorted(r_values)
    median_r = sorted_r[len(sorted_r) // 2] if sorted_r else None

    return HistoricalStats(
        occurrences=occurrences,
        win_rate=win_rate,
        loss_rate=(1.0 - win_rate) if win_rate is not None else None,
        avg_r=(sum(r_values) / len(r_values)) if r_values else None,
        median_r=median_r,
        profit_factor=profit_factor,
        avg_hold_bars=(sum(hold_bars) / len(hold_bars)) if hold_bars else None,
        max_drawdown=None,
        mfe=(sum(mfe_values) / len(mfe_values)) if mfe_values else None,
        mae=(sum(mae_values) / len(mae_values)) if mae_values else None,
        confidence_interval_95=None,
    )


class SQLAlchemyHistoricalStatsProvider(HistoricalStatsProvider):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        return await get_stats_for_condition(self._session, condition_key)
