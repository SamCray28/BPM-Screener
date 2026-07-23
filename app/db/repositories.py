"""Query layer over the Behavioral Database.

`SQLAlchemyHistoricalStatsProvider` is the concrete implementation of
`app.providers.base.HistoricalStatsProvider` this whole schema exists
to support — plug this in instead of `MockHistoricalStatsProvider` once
the database in app/db/models.py is actually populated, and every
downstream engine (score_historical, score_behavioral's Historical
Similarity and Forecast Reliability factors) starts working from real
evidence with no other code changes required.

Same caveat as everywhere else touching SQLAlchemy in this project:
syntax-checked (py_compile) in this sandbox, not executed against a
real database — there's no network access here to install SQLAlchemy
or connect to Postgres.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import BehavioralSnapshot, BehavioralTransition, TradeOutcome
from app.models.snapshot import HistoricalStats
from app.providers.base import HistoricalStatsProvider


def record_snapshot(
    session: Session,
    *,
    symbol: str,
    timeframe: str,
    bpm_mode: str,
    confirmed_state: str,
    confirmed_direction: str,
    bo_status: str,
    mc_status: str,
    pressure_efficiency: float,
    acceptance_status: str,
    bes_scenario: str,
    forecast_bias: Optional[str] = None,
    source_event_id: Optional[str] = None,
) -> BehavioralSnapshot:
    snapshot = BehavioralSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        bpm_mode=bpm_mode,
        confirmed_state=confirmed_state,
        confirmed_direction=confirmed_direction,
        bo_status=bo_status,
        mc_status=mc_status,
        pressure_efficiency=pressure_efficiency,
        acceptance_status=acceptance_status,
        bes_scenario=bes_scenario,
        forecast_bias=forecast_bias,
        condition_key=f"{confirmed_state}|{confirmed_direction}|{bes_scenario}",
        source_event_id=source_event_id,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_stats_for_condition(session: Session, condition_key: str) -> HistoricalStats:
    """Aggregate every TradeOutcome linked to a BehavioralSnapshot with
    this condition_key into a HistoricalStats object — the same shape
    app/engines/historical.py already knows how to consume."""
    stmt = (
        select(TradeOutcome)
        .join(BehavioralSnapshot, TradeOutcome.snapshot_id == BehavioralSnapshot.id)
        .where(BehavioralSnapshot.condition_key == condition_key)
        .where(TradeOutcome.r_multiple.is_not(None))
    )
    outcomes = list(session.execute(stmt).scalars().all())
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
        max_drawdown=None,  # requires equity-curve reconstruction, not just per-trade R
        mfe=(sum(mfe_values) / len(mfe_values)) if mfe_values else None,
        mae=(sum(mae_values) / len(mae_values)) if mae_values else None,
        confidence_interval_95=None,  # left to the caller / a stats library — not computed here
    )


def get_transition_frequency(session: Session, symbol: str, from_state: str, to_state: str) -> int:
    stmt = (
        select(func.count())
        .select_from(BehavioralTransition)
        .where(BehavioralTransition.symbol == symbol)
        .where(BehavioralTransition.from_state == from_state)
        .where(BehavioralTransition.to_state == to_state)
    )
    return session.execute(stmt).scalar_one()


class SQLAlchemyHistoricalStatsProvider(HistoricalStatsProvider):
    """Real HistoricalStatsProvider backed by the Behavioral Database,
    for use in place of MockHistoricalStatsProvider once the schema in
    app/db/models.py is populated with real trade outcomes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        return get_stats_for_condition(self._session, condition_key)
