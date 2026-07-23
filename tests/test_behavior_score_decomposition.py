import unittest

from app.config import HistoricalConfig
from app.engines.behavioral import score_behavioral
from app.models.snapshot import BehavioralData, HistoricalStats
from app.research import all_research_cards, get_research_card


class TestBehaviorScoreDecomposition(unittest.TestCase):
    def _sample_data(self, **overrides) -> BehavioralData:
        base = dict(
            confirmed_state="Expansion",
            confirmed_direction="Bullish",
            bo_status="Confirmed",
            mc_status="Locked",
            pressure_efficiency=70.0,
            acceptance_status="Strong",
            bes_scenario="BES-2 Momentum (MCZ-RZ)",
        )
        base.update(overrides)
        return BehavioralData(**base)

    def test_seven_factors_present_with_expected_weights(self):
        score = score_behavioral(self._sample_data())
        names_and_weights = {f.name: f.weight for f in score.contributing_factors}
        expected = {
            "Acceptance": 0.22,
            "Pressure": 0.18,
            "Structure": 0.19,
            "Forecast Reliability": 0.14,
            "Behavioral Stability": 0.09,
            "Transition Risk": 0.08,
            "Historical Similarity": 0.10,
        }
        self.assertEqual(set(names_and_weights.keys()), set(expected.keys()))
        for name, weight in expected.items():
            self.assertAlmostEqual(names_and_weights[name], weight, places=6)

    def test_weights_sum_to_one(self):
        score = score_behavioral(self._sample_data())
        self.assertAlmostEqual(score.factor_weight_sum(), 1.0, places=6)

    def test_missing_optional_inputs_lowers_confidence(self):
        rich = score_behavioral(
            self._sample_data(forecast_bias="Continuation Bias", bars_in_confirmed_state=15, recent_transition_count=0),
            historical=HistoricalStats(occurrences=50, win_rate=0.6),
            historical_config=HistoricalConfig(min_sample_size=20),
        )
        sparse = score_behavioral(self._sample_data())  # no forecast_bias/bars/transitions/historical
        self.assertGreater(rich.confidence, sparse.confidence)

    def test_uncalibrated_forecast_bias_scores_low(self):
        score = score_behavioral(
            self._sample_data(forecast_bias="Continuation Bias"),
            historical=HistoricalStats(occurrences=2),  # below default min_sample_size
            historical_config=HistoricalConfig(min_sample_size=20),
        )
        forecast_factor = next(f for f in score.contributing_factors if f.name == "Forecast Reliability")
        self.assertLess(forecast_factor.value, 40.0)


class TestResearchEngine(unittest.TestCase):
    _SUB_FACTOR_NAMES = [
        "Acceptance", "Pressure", "Structure", "Forecast Reliability",
        "Behavioral Stability", "Transition Risk", "Historical Similarity",
    ]

    def test_every_sub_factor_has_a_research_card(self):
        for name in self._SUB_FACTOR_NAMES:
            card = get_research_card(name)
            self.assertIsNotNone(card, f"missing research card for {name}")

    def test_every_research_card_has_all_six_sections_filled(self):
        for name, card in all_research_cards().items():
            self.assertTrue(card.definition.strip(), name)
            self.assertTrue(card.research_basis, name)
            self.assertTrue(card.calculation.strip(), name)
            self.assertTrue(card.evidence.strip(), name)
            self.assertTrue(card.confidence_notes.strip(), name)
            self.assertTrue(card.limitations.strip(), name)

    def test_factors_link_to_a_resolvable_research_card(self):
        from app.engines.behavioral import score_behavioral
        from app.models.snapshot import BehavioralData

        score = score_behavioral(BehavioralData(
            confirmed_state="Expansion", confirmed_direction="Bullish",
            bo_status="Confirmed", mc_status="Locked", pressure_efficiency=70.0,
            acceptance_status="Strong", bes_scenario="BES-2 Momentum (MCZ-RZ)",
        ))
        for f in score.contributing_factors:
            self.assertIsNotNone(f.research_key)
            self.assertIsNotNone(get_research_card(f.research_key))


if __name__ == "__main__":
    unittest.main()
