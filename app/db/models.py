"""The Behavioral Database schema.

This is the backing store the spec describes as BPM's real competitive
advantage: every behavioral snapshot, trade outcome, state transition,
forecast, acceptance event, pressure burst, earnings event, and news
catalyst, kept indefinitely and queryable.

Design notes:

- Uses SQLAlchemy 2.x to match the existing bpm-python receiver's stack
  (same Postgres instance could plausibly host both). This sandbox has
  no network access, so this file is syntax-checked (py_compile) but
  NOT executed against a real database here — same limitation noted for
  bpm-python's models.py.
- `condition_key` (state|direction|bes_scenario) is the same string
  app/engines/ranking.py._condition_key() builds, so a real
  HistoricalStatsProvider implementation can join against it directly.
- BehavioralSnapshot is the spine: every other table either references
  it directly (TradeOutcome, AcceptanceEvent, PressureBurstEvent) or
  can be correlated to it by symbol + timestamp (EarningsEventRecord,
  NewsCatalystRecord, BehavioralTransition).
- Nothing here computes anything — this is pure storage. The engines
  in app/engines/ are what turn rows in these tables into
  ScoreExplanation objects; a real HistoricalStatsProvider
  implementation queries this schema and returns a HistoricalStats
  object built from the results.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class BehavioralSnapshot(Base):
    """One row per confirmed BPM behavioral read (mirrors the bpm-python
    receiver's TelemetryEvent, but this is the long-term research store,
    not the live receipt log — a real deployment might populate this
    table FROM that one)."""

    __tablename__ = "behavioral_snapshots"
    __table_args__ = (
        Index("ix_snapshots_symbol_time", "symbol", "captured_at"),
        Index("ix_snapshots_condition_key", "condition_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    bpm_mode: Mapped[str] = mapped_column(String(16), nullable=False)

    confirmed_state: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    bo_status: Mapped[str] = mapped_column(String(32), nullable=False)
    mc_status: Mapped[str] = mapped_column(String(32), nullable=False)
    pressure_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    acceptance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    bes_scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    forecast_bias: Mapped[str] = mapped_column(String(32), nullable=True)

    # "state|direction|bes_scenario" — must match
    # app/engines/ranking.py._condition_key() exactly.
    condition_key: Mapped[str] = mapped_column(String(160), nullable=False)

    # link back to the bpm-python receiver's TelemetryEvent.event_id, if
    # this snapshot originated from live telemetry rather than backfill.
    source_event_id: Mapped[str] = mapped_column(String(256), nullable=True)

    trade_outcomes: Mapped[list["TradeOutcome"]] = relationship(back_populates="snapshot")
    acceptance_events: Mapped[list["AcceptanceEvent"]] = relationship(back_populates="snapshot")
    pressure_bursts: Mapped[list["PressureBurstEvent"]] = relationship(back_populates="snapshot")


class TradeOutcome(Base):
    """The realized outcome (if any) of a behavioral condition — this is
    what score_historical() ultimately aggregates into win rate, profit
    factor, avg R, MFE/MAE, etc."""

    __tablename__ = "trade_outcomes"
    __table_args__ = (Index("ix_outcomes_snapshot", "snapshot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("behavioral_snapshots.id"), nullable=False)

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=True)
    is_win: Mapped[bool] = mapped_column(Boolean, nullable=True)
    hold_bars: Mapped[int] = mapped_column(Integer, nullable=True)
    max_favorable_excursion: Mapped[float] = mapped_column(Float, nullable=True)
    max_adverse_excursion: Mapped[float] = mapped_column(Float, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshot: Mapped["BehavioralSnapshot"] = relationship(back_populates="trade_outcomes")


class BehavioralTransition(Base):
    """One row per confirmed state change (e.g. Negotiation -> Expansion).
    This is the real data source app/engines/behavioral.py's Transition
    Risk factor is designed to eventually query, replacing its current
    heuristic with actual transition-frequency statistics."""

    __tablename__ = "behavioral_transitions"
    __table_args__ = (Index("ix_transitions_symbol_time", "symbol", "occurred_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    bars_in_prior_state: Mapped[int] = mapped_column(Integer, nullable=True)


class ForecastRecord(Base):
    """One row per forecast bias Pine reported, plus (once known) whether
    it was realized. This is exactly the table Forecast Reliability
    needs to become a real calibrated statistic instead of a proxy."""

    __tablename__ = "forecast_records"
    __table_args__ = (Index("ix_forecast_symbol_time", "symbol", "issued_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    forecast_bias: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_bars: Mapped[int] = mapped_column(Integer, nullable=False)
    realized_outcome: Mapped[str] = mapped_column(String(32), nullable=True)  # populated after the horizon passes
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)


class AcceptanceEvent(Base):
    """One row per level-acceptance read (BO/MCZ/RZ/BE/BDZ/CT/MC) — the
    real backing data for the Acceptance sub-factor and for the BIS
    spec's "every acceptance event" requirement."""

    __tablename__ = "acceptance_events"
    __table_args__ = (Index("ix_acceptance_snapshot", "snapshot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("behavioral_snapshots.id"), nullable=False)

    level_name: Mapped[str] = mapped_column(String(16), nullable=False)  # BO/MCZ/RZ/BE/BDZ/CT/MC
    acceptance_status: Mapped[str] = mapped_column(String(32), nullable=False)
    penetration_depth_atr: Mapped[float] = mapped_column(Float, nullable=True)
    time_held_bars: Mapped[int] = mapped_column(Integer, nullable=True)

    snapshot: Mapped["BehavioralSnapshot"] = relationship(back_populates="acceptance_events")


class PressureBurstEvent(Base):
    """One row per notable pressure-efficiency spike — the real backing
    data for the Pressure sub-factor's evidence base."""

    __tablename__ = "pressure_burst_events"
    __table_args__ = (Index("ix_pressure_snapshot", "snapshot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("behavioral_snapshots.id"), nullable=False)

    pressure_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    snapshot: Mapped["BehavioralSnapshot"] = relationship(back_populates="pressure_bursts")


class EarningsEventRecord(Base):
    __tablename__ = "earnings_event_records"
    __table_args__ = (Index("ix_earnings_symbol_time", "symbol", "reported_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    eps_actual: Mapped[float] = mapped_column(Float, nullable=True)
    eps_estimate: Mapped[float] = mapped_column(Float, nullable=True)
    surprise_pct: Mapped[float] = mapped_column(Float, nullable=True)
    reaction_pct: Mapped[float] = mapped_column(Float, nullable=True)


class NewsCatalystRecord(Base):
    __tablename__ = "news_catalyst_records"
    __table_args__ = (Index("ix_news_symbol_time", "symbol", "published_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped[str] = mapped_column(String(64), nullable=False)
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    relevance: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_behavioral_impact: Mapped[str] = mapped_column(String(16), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
