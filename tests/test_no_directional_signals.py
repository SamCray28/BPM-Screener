import unittest

from app.safeguards import DirectionalLanguageError, assert_no_directional_language


class TestNoDirectionalSignals(unittest.TestCase):
    def test_clean_text_passes(self):
        assert_no_directional_language("Behavioral state is Expansion with strong acceptance.")

    def test_buy_is_rejected(self):
        with self.assertRaises(DirectionalLanguageError):
            assert_no_directional_language("This looks like a good buy setup.")

    def test_sell_short_long_are_rejected(self):
        for word in ("sell", "short", "long", "BUY", "Long"):
            with self.assertRaises(DirectionalLanguageError):
                assert_no_directional_language(f"Consider going {word} here.")


if __name__ == "__main__":
    unittest.main()
