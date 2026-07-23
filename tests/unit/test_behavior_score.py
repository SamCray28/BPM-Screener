import unittest

from app.engines.behavioral import score_behavioral
from app.engines.weights import HistoricalConfig
from app.models.snapshot import BehavioralData, HistoricalStats


class TestBehaviorScore(unittest.TestCase):
    def _data(self, **overrides) -> BehavioralData:
        base = dict(
            confirmed_state="Expansion", confirmed_direction="Bullish", bo_status="Confirmed",
            mc_status="Locked", pressure_efficiency=70.0, acceptance_status="Strong",
            bes_scenario="BES-2 Momentum (MCZ-RZ)",
        )
        base.update(overrides)
        return BehavioralData(**base)

    def test_seven_factors_with_correct_weights(self):
        score = score_behavioral(self._data())
        weights = {f.name: f.weight for f in score.contributing_factors}
        expected = {
            "Acceptance": 0.22, "Pressure": 0.18, "Structure": 0.19, "Forecast Reliability": 0.14,
            "Behavioral Stability": 0.09, "Transition Risk": 0.08, "Historical Similarity": 0.10,
        }
        self.assertEqual(set(weights), set(expected))
        for name, w in expected.items():
            self.assertAlmostEqual(weights[name], w, places=6)
        self.assertAlmostEqual(score.factor_weight_sum(), 1.0, places=6)

    def test_uncalibrated_forecast_scores_low(self):
        score = score_behavioral(
            self._data(forecast_bias="Continuation Bias"),
            historical=HistoricalStats(occurrences=2),
            historical_config=HistoricalConfig(min_sample_size=20),
        )
        forecast = next(f for f in score.contributing_factors if f.name == "Forecast Reliability")
        self.assertLess(forecast.value, 40.0)

    def test_calibrated_forecast_scores_higher(self):
        score = score_behavioral(
            self._data(forecast_bias="Continuation Bias"),
            historical=HistoricalStats(occurrences=80),
            historical_config=HistoricalConfig(min_sample_size=20),
        )
        forecast = next(f for f in score.contributing_factors if f.name == "Forecast Reliability")
        self.assertGreater(forecast.value, 60.0)

    def test_transition_risk_is_inverted(self):
        # Strong acceptance + Expansion => low raw risk => HIGH displayed value.
        calm = score_behavioral(self._data(confirmed_state="Expansion", acceptance_status="Strong"))
        # Compression + Failed acceptance => high raw risk => LOW displayed value.
        risky = score_behavioral(self._data(confirmed_state="Compression", acceptance_status="Failed"))
        calm_val = next(f for f in calm.contributing_factors if f.name == "Transition Risk").value
        risky_val = next(f for f in risky.contributing_factors if f.name == "Transition Risk").value
        self.assertGreater(calm_val, risky_val)

    def test_missing_optional_data_lowers_confidence(self):
        rich = score_behavioral(
            self._data(forecast_bias="Continuation Bias", bars_in_confirmed_state=15, recent_transition_count=0),
            historical=HistoricalStats(occurrences=50, win_rate=0.6),
        )
        sparse = score_behavioral(self._data())
        self.assertGreater(rich.confidence, sparse.confidence)


if __name__ == "__main__":
    unittest.main()
