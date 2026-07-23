import unittest

from app.config import HistoricalConfig, ScoringWeights, UniverseConfig
from app.engines.ranking import build_ranking
from app.providers.mock_provider import (
    MockBehavioralDataProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
)


class TestRankingPipeline(unittest.TestCase):
    def _build(self):
        return build_ranking(
            market_provider=MockMarketDataProvider(),
            behavioral_provider=MockBehavioralDataProvider(),
            news_provider=MockNewsProvider(),
            historical_provider=MockHistoricalStatsProvider(),
            universe_config=UniverseConfig(),
            historical_config=HistoricalConfig(min_sample_size=20),
            scoring_weights=ScoringWeights(),
        )

    def test_produces_ranked_list_with_valid_ranks(self):
        ranking = self._build()
        self.assertGreater(len(ranking), 0)
        ranks = [r.behavioral_opportunity_rank for r in ranking]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks[0], 1)

    def test_every_symbol_has_explained_scores(self):
        for r in self._build():
            self.assertTrue(r.overall_score.contributing_factors)
            for sub in r.sub_scores:
                self.assertTrue(sub.contributing_factors)
                self.assertTrue(sub.methodology.strip())

    def test_no_symbol_has_directional_language_in_output(self):
        # validate_ranked_symbol already runs inside build_ranking(); this
        # re-asserts it holds for every symbol actually returned.
        from app.safeguards import validate_ranked_symbol
        for r in self._build():
            validate_ranked_symbol(r)  # should not raise


if __name__ == "__main__":
    unittest.main()
