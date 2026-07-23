"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-23

Hand-written to match app/models/db_models.py exactly, since there is
no live database in this sandbox to run `alembic revision --autogenerate`
against. Review/regenerate against a real Postgres instance before
trusting this in production — see alembic/env.py's docstring.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", sa.String(256), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("formula_version", sa.String(64), nullable=False),
        sa.Column("configuration_id", sa.String(128), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("exchange", sa.String(64), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("bpm_mode", sa.String(16), nullable=False),
        sa.Column("bar_open_time", sa.BigInteger, nullable=False),
        sa.Column("bar_close_time", sa.BigInteger, nullable=False),
        sa.Column("confirmed_state", sa.String(32), nullable=False),
        sa.Column("confirmed_direction", sa.String(16), nullable=False),
        sa.Column("bo_status", sa.String(32), nullable=False),
        sa.Column("active_bo_price", sa.Float, nullable=False),
        sa.Column("mc_status", sa.String(32), nullable=False),
        sa.Column("active_mc_price", sa.Float, nullable=False),
        sa.Column("pressure_efficiency", sa.Float, nullable=False),
        sa.Column("acceptance_status", sa.String(32), nullable=False),
        sa.Column("bes_scenario", sa.String(64), nullable=False),
        sa.Column("raw_payload", sa.Text, nullable=False),
        sa.UniqueConstraint("event_id", name="uq_telemetry_events_event_id"),
    )
    op.create_index("ix_telemetry_events_event_id", "telemetry_events", ["event_id"])
    op.create_index("ix_telemetry_events_symbol", "telemetry_events", ["symbol"])
    op.create_index("ix_telemetry_events_timeframe", "telemetry_events", ["timeframe"])
    op.create_index("ix_telemetry_events_bpm_mode", "telemetry_events", ["bpm_mode"])

    op.create_table(
        "behavioral_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("bpm_mode", sa.String(16), nullable=False),
        sa.Column("confirmed_state", sa.String(32), nullable=False),
        sa.Column("confirmed_direction", sa.String(16), nullable=False),
        sa.Column("bo_status", sa.String(32), nullable=False),
        sa.Column("mc_status", sa.String(32), nullable=False),
        sa.Column("pressure_efficiency", sa.Float, nullable=False),
        sa.Column("acceptance_status", sa.String(32), nullable=False),
        sa.Column("bes_scenario", sa.String(64), nullable=False),
        sa.Column("forecast_bias", sa.String(32), nullable=True),
        sa.Column("condition_key", sa.String(160), nullable=False),
        sa.Column("source_event_id", sa.String(256), nullable=True),
    )
    op.create_index("ix_snapshots_symbol_time", "behavioral_snapshots", ["symbol", "captured_at"])
    op.create_index("ix_snapshots_condition_key", "behavioral_snapshots", ["condition_key"])

    op.create_table(
        "trade_outcomes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.Integer, sa.ForeignKey("behavioral_snapshots.id"), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("r_multiple", sa.Float, nullable=True),
        sa.Column("is_win", sa.Boolean, nullable=True),
        sa.Column("hold_bars", sa.Integer, nullable=True),
        sa.Column("max_favorable_excursion", sa.Float, nullable=True),
        sa.Column("max_adverse_excursion", sa.Float, nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outcomes_snapshot", "trade_outcomes", ["snapshot_id"])

    op.create_table(
        "behavioral_transitions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=False),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("bars_in_prior_state", sa.Integer, nullable=True),
    )
    op.create_index("ix_transitions_symbol_time", "behavioral_transitions", ["symbol", "occurred_at"])

    op.create_table(
        "forecast_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_bias", sa.String(32), nullable=False),
        sa.Column("horizon_bars", sa.Integer, nullable=False),
        sa.Column("realized_outcome", sa.String(32), nullable=True),
        sa.Column("was_correct", sa.Boolean, nullable=True),
    )
    op.create_index("ix_forecast_symbol_time", "forecast_records", ["symbol", "issued_at"])

    op.create_table(
        "acceptance_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.Integer, sa.ForeignKey("behavioral_snapshots.id"), nullable=False),
        sa.Column("level_name", sa.String(16), nullable=False),
        sa.Column("acceptance_status", sa.String(32), nullable=False),
        sa.Column("penetration_depth_atr", sa.Float, nullable=True),
        sa.Column("time_held_bars", sa.Integer, nullable=True),
    )
    op.create_index("ix_acceptance_snapshot", "acceptance_events", ["snapshot_id"])

    op.create_table(
        "pressure_burst_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.Integer, sa.ForeignKey("behavioral_snapshots.id"), nullable=False),
        sa.Column("pressure_efficiency", sa.Float, nullable=False),
        sa.Column("magnitude", sa.Float, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pressure_snapshot", "pressure_burst_events", ["snapshot_id"])

    op.create_table(
        "earnings_event_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eps_actual", sa.Float, nullable=True),
        sa.Column("eps_estimate", sa.Float, nullable=True),
        sa.Column("surprise_pct", sa.Float, nullable=True),
        sa.Column("reaction_pct", sa.Float, nullable=True),
    )
    op.create_index("ix_earnings_symbol_time", "earnings_event_records", ["symbol", "reported_at"])

    op.create_table(
        "news_catalyst_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("headline", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("relevance", sa.Float, nullable=True),
        sa.Column("estimated_behavioral_impact", sa.String(16), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
    )
    op.create_index("ix_news_symbol_time", "news_catalyst_records", ["symbol", "published_at"])

    op.create_table(
        "ranking_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("universe_size", sa.Integer, nullable=False),
    )

    op.create_table(
        "ranking_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("ranking_runs.id"), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("opportunity_score", sa.Float, nullable=False),
        sa.Column("behavior_score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("full_result_json", sa.Text, nullable=False),
    )
    op.create_index("ix_ranking_results_run_symbol", "ranking_results", ["run_id", "symbol"])

    op.create_table(
        "webhook_audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=True),
        sa.Column("event_id", sa.String(256), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("source_ip", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhook_audit_log")
    op.drop_table("ranking_results")
    op.drop_table("ranking_runs")
    op.drop_table("news_catalyst_records")
    op.drop_table("earnings_event_records")
    op.drop_table("pressure_burst_events")
    op.drop_table("acceptance_events")
    op.drop_table("forecast_records")
    op.drop_table("behavioral_transitions")
    op.drop_table("trade_outcomes")
    op.drop_table("behavioral_snapshots")
    op.drop_table("telemetry_events")
