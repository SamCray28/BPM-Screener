import unittest

from app.safeguards import DirectionalLanguageError, UnexplainedScoreError, assert_explained, assert_no_directional_language
from app.models.evidence import EvidenceFactor, ScoreExplanation


class TestNoDirectionalSignals(unittest.TestCase):
    def test_clean_text_passes(self):
        assert_no_directional_language("Behavioral state is Expansion with strong acceptance.")

    def test_buy_sell_long_short_all_rejected(self):
        for word in ("buy", "sell", "long", "short", "BUY", "Short"):
            with self.assertRaises(DirectionalLanguageError):
                assert_no_directional_language(f"Consider going {word} here.")


class TestExplainabilityGuard(unittest.TestCase):
    def test_valid_score_passes(self):
        score = ScoreExplanation(
            score_name="Test", value=50.0, confidence=0.5, methodology="m",
            contributing_factors=[EvidenceFactor("X", 50.0, 1.0, "d", "s")],
        )
        assert_explained(score)  # should not raise

    def test_score_construction_itself_rejects_empty_factors(self):
        with self.assertRaises(ValueError):
            ScoreExplanation(score_name="Bad", value=50.0, confidence=0.5, methodology="m", contributing_factors=[])


if __name__ == "__main__":
    unittest.main()
