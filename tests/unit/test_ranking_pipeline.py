import unittest

from app.engines.ranking import build_ranking
from app.engines.weights import HistoricalConfig, OpportunityWeights, UniverseConfig
from app.providers.mock.mock_providers import (
    MockBehavioralDataProvider,
    MockCorporateEventsProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
)
from app.safeguards import validate_ranked_symbol


class TestRankingPipeline(unittest.IsolatedAsyncioTestCase):
    async def _build(self, fetch_multi_timeframe: bool = True):
        return await build_ranking(
            market_provider=MockMarketDataProvider(),
            behavioral_provider=MockBehavioralDataProvider(),
            news_provider=MockNewsProvider(),
            historical_provider=MockHistoricalStatsProvider(),
            universe_config=UniverseConfig(),
            historical_config=HistoricalConfig(min_sample_size=20),
            opportunity_weights=OpportunityWeights(),
            corporate_events_provider=MockCorporateEventsProvider(),
            fetch_multi_timeframe=fetch_multi_timeframe,
        )

    async def test_produces_ranked_list_with_sequential_ranks(self):
        ranking = await self._build()
        self.assertGreater(len(ranking), 0)
        ranks = [r.rank for r in ranking]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks[0], 1)

    async def test_every_symbol_passes_output_validation(self):
        for r in await self._build():
            validate_ranked_symbol(r)  # should not raise

    async def test_every_score_has_contributing_factors(self):
        for r in await self._build():
            self.assertTrue(r.behavior_score.contributing_factors)
            self.assertTrue(r.opportunity_score.contributing_factors)
            for s in r.sub_scores:
                self.assertTrue(s.contributing_factors)

    async def test_works_without_multi_timeframe_data(self):
        # exercises the Trend Score's graceful-degradation path
        ranking = await self._build(fetch_multi_timeframe=False)
        self.assertGreater(len(ranking), 0)
        for r in ranking:
            trend = next(s for s in r.sub_scores if s.score_name == "Trend Score")
            self.assertLessEqual(trend.confidence, 0.2)

    async def test_no_insider_transaction_language_leaks(self):
        # MockCorporateEventsProvider genuinely uses "Buy"/"Sell" as raw
        # transaction_type values; this proves the neutral-language
        # translation holds across the full pipeline, not just in isolation.
        for r in await self._build():
            for evidence in r.supporting_evidence:
                self.assertNotIn(" buy ", f" {evidence.lower()} ")
                self.assertNotIn(" sell ", f" {evidence.lower()} ")


if __name__ == "__main__":
    unittest.main()
