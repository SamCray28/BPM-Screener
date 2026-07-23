"""Background scheduler. Runs the ranking pipeline on a timer
(RANKING_REFRESH_SECONDS) and stores the result in both the fast-path
in-memory cache (app/ranking_cache.py) and the persisted
ranking_runs/ranking_results tables for /history.

Multi-instance safety: a Render (or any horizontally-scaled) deployment
that runs more than one web instance would otherwise run this loop
once PER INSTANCE, duplicating ranking runs. When DATABASE_URL points
at Postgres, this module uses a session-held pg_try_advisory_lock as a
simple leader-election guard — only the instance holding the lock runs
the loop; the others retry acquisition every SCHEDULER_LEADER_RETRY_SECONDS
and take over automatically if the leader disappears (Postgres releases
the lock when its holding connection closes). Against SQLite (local
dev/test), leader election is skipped entirely — that only happens in
a single-instance setup where it isn't needed.

Verification status: the ranking logic itself (build_ranking, caching)
is exercised by tests/unit/test_ranking_pipeline.py. The Postgres
advisory-lock acquisition/release has NOT been tested against a real
Postgres instance in this sandbox — no network access here. Review
_is_postgres_url() and the lock queries against your actual asyncpg
setup before relying on this under real multi-instance load.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import Settings
from app.database import AsyncSessionLocal, engine
from app.engines.ranking import build_ranking
from app.engines.weights import HistoricalConfig, OpportunityWeights, UniverseConfig
from app.models.db_models import RankingResult, RankingRun
from app.providers.factory import (
    build_behavioral_data_provider,
    build_corporate_events_provider,
    build_historical_stats_provider,
    build_market_data_provider,
    build_news_provider,
)
from app.ranking_cache import ranking_cache

logger = logging.getLogger("bpm.scheduler")


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith("postgresql")


def _score_to_jsonable(score) -> dict:
    return {
        "score_name": score.score_name, "value": score.value, "confidence": score.confidence,
        "methodology": score.methodology, "sample_size": score.sample_size,
        "historical_support": score.historical_support, "is_original_to_bpm": score.is_original_to_bpm,
        "contributing_factors": [dataclasses.asdict(f) for f in score.contributing_factors],
    }


def _ranked_symbol_to_jsonable(r) -> dict:
    return {
        "rank": r.rank, "symbol": r.symbol,
        "behavior_score": _score_to_jsonable(r.behavior_score),
        "opportunity_score": _score_to_jsonable(r.opportunity_score),
        "sub_scores": [_score_to_jsonable(s) for s in r.sub_scores],
        "historical_expectancy": r.historical_expectancy, "confidence": r.confidence,
        "historical_sample_size": r.historical_sample_size, "behavior_state": r.behavior_state,
        "acceptance": r.acceptance, "pressure": r.pressure, "trend_summary": r.trend_summary,
        "liquidity_summary": r.liquidity_summary, "recent_news": r.recent_news,
        "estimated_hold_duration": r.estimated_hold_duration, "capital_efficiency": r.capital_efficiency,
        "primary_risks": r.primary_risks, "reasons_for_ranking": r.reasons_for_ranking,
        "supporting_evidence": r.supporting_evidence,
    }


async def run_ranking_once(settings: Settings) -> None:
    async with AsyncSessionLocal() as session:
        market_provider = build_market_data_provider(settings)
        behavioral_provider = build_behavioral_data_provider(settings, session)
        news_provider = build_news_provider(settings)
        historical_provider = build_historical_stats_provider(settings, session)
        corporate_events_provider = build_corporate_events_provider(settings)

        universe_config = UniverseConfig(
            max_share_price=settings.UNIVERSE_MAX_SHARE_PRICE,
            min_avg_daily_volume=settings.UNIVERSE_MIN_AVG_DAILY_VOLUME,
            min_avg_daily_dollar_volume=settings.UNIVERSE_MIN_AVG_DAILY_DOLLAR_VOLUME,
            min_relative_volume=settings.UNIVERSE_MIN_RELATIVE_VOLUME,
        )
        historical_config = HistoricalConfig(min_sample_size=settings.HISTORICAL_MIN_SAMPLE_SIZE)

        results = await build_ranking(
            market_provider=market_provider,
            behavioral_provider=behavioral_provider,
            news_provider=news_provider,
            historical_provider=historical_provider,
            universe_config=universe_config,
            historical_config=historical_config,
            opportunity_weights=OpportunityWeights(),
            corporate_events_provider=corporate_events_provider,
        )

        ranking_cache.set(results)

        run = RankingRun(universe_size=len(results))
        session.add(run)
        await session.flush()
        for r in results:
            session.add(RankingResult(
                run_id=run.id, rank=r.rank, symbol=r.symbol,
                opportunity_score=r.opportunity_score.value, behavior_score=r.behavior_score.value,
                confidence=r.confidence, full_result_json=json.dumps(_ranked_symbol_to_jsonable(r)),
            ))
        await session.commit()

        logger.info("ranking run complete: %d symbols ranked", len(results))


async def _try_acquire_leader_lock(settings: Settings) -> Optional[AsyncConnection]:
    """Attempts to acquire a session-held Postgres advisory lock. Returns
    the open connection holding the lock (caller must keep it open for
    as long as it wants to remain leader, and close it to release the
    lock), or None if another instance currently holds it."""
    conn = await engine.connect()
    result = await conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": settings.SCHEDULER_LEADER_LOCK_KEY})
    acquired = bool(result.scalar())
    if not acquired:
        await conn.close()
        return None
    return conn


async def _release_leader_lock(conn: AsyncConnection, settings: Settings) -> None:
    try:
        await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": settings.SCHEDULER_LEADER_LOCK_KEY})
    finally:
        await conn.close()


async def scheduler_loop(settings: Settings) -> None:
    use_leader_election = settings.SCHEDULER_LEADER_ELECTION_ENABLED and _is_postgres_url(settings.DATABASE_URL)

    if not use_leader_election:
        # Single-instance assumption (SQLite dev/test, or leader election
        # explicitly disabled) — just run the loop directly.
        while True:
            try:
                await run_ranking_once(settings)
            except Exception:  # noqa: BLE001 — one bad run must never kill the loop
                logger.exception("ranking run failed; will retry on next interval")
            await asyncio.sleep(settings.RANKING_REFRESH_SECONDS)
        return

    lock_conn: Optional[AsyncConnection] = None
    try:
        while True:
            if lock_conn is None:
                lock_conn = await _try_acquire_leader_lock(settings)
                if lock_conn is None:
                    logger.info(
                        "another instance holds the scheduler leader lock; retrying in %ds",
                        settings.SCHEDULER_LEADER_RETRY_SECONDS,
                    )
                    await asyncio.sleep(settings.SCHEDULER_LEADER_RETRY_SECONDS)
                    continue
                logger.info("acquired scheduler leader lock — this instance will run ranking")

            try:
                await run_ranking_once(settings)
            except Exception:  # noqa: BLE001 — one bad run must never kill the loop
                logger.exception("ranking run failed; will retry on next interval")
            await asyncio.sleep(settings.RANKING_REFRESH_SECONDS)
    finally:
        if lock_conn is not None:
            await _release_leader_lock(lock_conn, settings)
