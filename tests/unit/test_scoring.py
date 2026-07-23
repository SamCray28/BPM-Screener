import unittest

from app.engines.historical import score_historical
from app.engines.scoring import combine_opportunity_score
from app.engines.weights import HistoricalConfig, OpportunityWeights
from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import HistoricalStats


class TestHistoricalScoreGating(unittest.TestCase):
    def test_below_threshold_zeroes_out(self):
        config = HistoricalConfig(min_sample_size=20)
        stats = HistoricalStats(occurrences=5, win_rate=0.9, profit_factor=3.0)
        result = score_historical(stats, config)
        self.assertEqual(result.value, 0.0)
        self.assertEqual(result.confidence, 0.0)

    def test_zero_occurrences_zeroes_out(self):
        result = score_historical(HistoricalStats(occurrences=0), HistoricalConfig(min_sample_size=20))
        self.assertEqual(result.confidence, 0.0)

    def test_above_threshold_produces_real_score(self):
        config = HistoricalConfig(min_sample_size=20)
        stats = HistoricalStats(occurrences=40, win_rate=0.6, profit_factor=1.8)
        result = score_historical(stats, config)
        self.assertGreater(result.value, 0.0)
        self.assertGreater(result.confidence, 0.0)
        self.assertEqual(result.sample_size, 40)


def _dummy_score(name: str, value: float, confidence: float) -> ScoreExplanation:
    return ScoreExplanation(
        score_name=name, value=value, confidence=confidence, methodology="test",
        contributing_factors=[EvidenceFactor("f", value, 1.0, "d", "s")],
    )


class TestOpportunityScoreCombination(unittest.TestCase):
    def test_weights_sum_and_bounds(self):
        weights = OpportunityWeights().normalized()
        total = weights.behavior + weights.structure + weights.liquidity + weights.historical + weights.trend + weights.news
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_low_confidence_component_pulls_overall_confidence_down(self):
        high_conf = [_dummy_score(n, 70.0, 0.9) for n in
                     ["Behavior Score", "Structure Score", "Liquidity Score", "Historical Score", "Trend Score", "News Score"]]
        mixed_conf = high_conf[:-1] + [_dummy_score("News Score", 70.0, 0.05)]

        weights = OpportunityWeights()
        high_result = combine_opportunity_score(*high_conf, weights=weights)
        mixed_result = combine_opportunity_score(*mixed_conf, weights=weights)

        self.assertLess(mixed_result.confidence, high_result.confidence)


if __name__ == "__main__":
    unittest.main()
