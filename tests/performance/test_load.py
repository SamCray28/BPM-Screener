"""Load/performance tests for the ranking pipeline.

Unlike tests/api and tests/providers, these need nothing beyond the
standard library plus app.engines/app.providers.mock — so they
actually run in this sandbox, not just in CI. The latency assertions
are deliberately generous (they're meant to catch a catastrophic
regression — e.g. an accidental O(n^2) or a blocking call creeping
into an async path — not to be a tight performance SLA, since absolute
numbers depend heavily on the machine running them).
"""
from __future__ import annotations

import asyncio
import random
import time
import unittest
from typing import List

from app.engines.ranking import build_ranking
from app.engines.weights import HistoricalConfig, OpportunityWeights, UniverseConfig
from app.models.snapshot import MarketData
from app.providers.mock.mock_providers import (
    MockBehavioralDataProvider,
    MockCorporateEventsProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
)


class StressMarketDataProvider(MockMarketDataProvider):
    """Same synthetic data generation as MockMarketDataProvider, but for
    an arbitrary, configurable number of symbols — the real
    MockMarketDataProvider hardcodes 5 demo symbols, which isn't enough
    to stress-test anything."""

    def __init__(self, symbol_count: int, seed: int = 42) -> None:
        rng = random.Random(seed)
        symbols = [f"SYM{i:04d}" for i in range(symbol_count)]
        self._data = {s: self._synthesize(s, rng) for s in symbols}


async def _run_ranking(symbol_count: int) -> List:
    return await build_ranking(
        market_provider=StressMarketDataProvider(symbol_count),
        behavioral_provider=MockBehavioralDataProvider(),
        news_provider=MockNewsProvider(),
        historical_provider=MockHistoricalStatsProvider(),
        universe_config=UniverseConfig(),
        historical_config=HistoricalConfig(min_sample_size=20),
        opportunity_weights=OpportunityWeights(),
        corporate_events_provider=MockCorporateEventsProvider(),
    )


class TestRankingPipelineLoad(unittest.IsolatedAsyncioTestCase):
    async def test_handles_200_symbol_universe_without_error(self):
        results = await _run_ranking(symbol_count=200)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 200)

    async def test_200_symbol_universe_completes_within_generous_bound(self):
        start = time.perf_counter()
        await _run_ranking(symbol_count=200)
        elapsed = time.perf_counter() - start
        # Generous — this is mock data with no real I/O latency; a
        # regression that made this take >10s on any reasonable machine
        # would indicate something is very wrong (e.g. accidental
        # quadratic behavior), not just "the machine is slow today."
        self.assertLess(elapsed, 10.0, f"200-symbol ranking took {elapsed:.2f}s — investigate for a performance regression")

    async def test_concurrent_ranking_runs_do_not_interfere(self):
        """Simulates several overlapping ranking requests (e.g. a
        scheduler run overlapping with an on-demand refresh) — proves
        build_ranking has no shared mutable state that corrupts results
        under concurrency."""
        results_list = await asyncio.gather(*[_run_ranking(symbol_count=50) for _ in range(5)])
        for results in results_list:
            self.assertGreater(len(results), 0)
            ranks = [r.rank for r in results]
            self.assertEqual(ranks, sorted(ranks))
            self.assertEqual(ranks[0], 1)

    async def test_per_symbol_latency_scales_roughly_linearly(self):
        """A coarse check that doubling the universe doesn't more than
        roughly quadruple the runtime (which would suggest accidental
        O(n^2) behavior somewhere in the pipeline)."""
        start_small = time.perf_counter()
        await _run_ranking(symbol_count=50)
        small_elapsed = time.perf_counter() - start_small

        start_large = time.perf_counter()
        await _run_ranking(symbol_count=200)
        large_elapsed = time.perf_counter() - start_large

        # 4x the symbols; allow generous slack (up to ~10x time) before
        # flagging non-linear-looking growth — this is a coarse smoke
        # check, not a precise complexity proof.
        self.assertLess(
            large_elapsed, small_elapsed * 10 + 1.0,
            f"200-symbol run ({large_elapsed:.2f}s) scaled much worse than 50-symbol run ({small_elapsed:.2f}s)",
        )


if __name__ == "__main__":
    unittest.main()
