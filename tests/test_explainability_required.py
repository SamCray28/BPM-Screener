import unittest

from app.models.evidence import EvidenceFactor, ScoreExplanation


class TestExplainabilityRequired(unittest.TestCase):
    def test_score_without_factors_is_rejected(self):
        with self.assertRaises(ValueError):
            ScoreExplanation(
                score_name="Bad Score", value=80.0, confidence=0.5,
                methodology="some method", contributing_factors=[],
            )

    def test_score_without_methodology_is_rejected(self):
        factor = EvidenceFactor("X", 50.0, 1.0, "desc", "src")
        with self.assertRaises(ValueError):
            ScoreExplanation(
                score_name="Bad Score", value=80.0, confidence=0.5,
                methodology="   ", contributing_factors=[factor],
            )

    def test_value_and_confidence_bounds_enforced(self):
        factor = EvidenceFactor("X", 50.0, 1.0, "desc", "src")
        with self.assertRaises(ValueError):
            ScoreExplanation(score_name="Bad", value=150.0, confidence=0.5,
                              methodology="m", contributing_factors=[factor])
        with self.assertRaises(ValueError):
            ScoreExplanation(score_name="Bad", value=50.0, confidence=1.5,
                              methodology="m", contributing_factors=[factor])

    def test_valid_score_constructs_cleanly(self):
        factor = EvidenceFactor("X", 50.0, 1.0, "desc", "src")
        score = ScoreExplanation(score_name="Good", value=50.0, confidence=0.5,
                                  methodology="m", contributing_factors=[factor])
        self.assertEqual(score.factor_weight_sum(), 1.0)


if __name__ == "__main__":
    unittest.main()
