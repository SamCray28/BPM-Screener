import unittest

from app.config import HistoricalConfig
from app.engines.historical import score_historical
from app.models.snapshot import HistoricalStats


class TestSampleThresholdGating(unittest.TestCase):
    def test_insufficient_sample_suppresses_probability(self):
        config = HistoricalConfig(min_sample_size=20)
        stats = HistoricalStats(occurrences=5, win_rate=0.9, profit_factor=3.0)
        result = score_historical(stats, config)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("Insufficient sample", result.historical_support or "")

    def test_zero_occurrences_suppresses_probability(self):
        config = HistoricalConfig(min_sample_size=20)
        stats = HistoricalStats(occurrences=0)
        result = score_historical(stats, config)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.sample_size, 0)

    def test_sufficient_sample_reports_probability(self):
        config = HistoricalConfig(min_sample_size=20)
        stats = HistoricalStats(
            occurrences=40, win_rate=0.6, profit_factor=1.8, avg_r=0.4, median_r=0.3,
            avg_hold_bars=10, confidence_interval_95=(0.45, 0.75),
        )
        result = score_historical(stats, config)
        self.assertGreater(result.confidence, 0.0)
        self.assertEqual(result.sample_size, 40)


if __name__ == "__main__":
    unittest.main()
