import unittest
from datetime import datetime, timedelta, timezone

from app.engines.multi_timeframe import score_multi_timeframe_trend
from app.models.snapshot import Bar, MultiTimeframeSnapshot, TimeframeSeries


def _make_bars(closes, base_time=None):
    base_time = base_time or datetime.now(timezone.utc)
    bars = []
    for i, c in enumerate(closes):
        bars.append(Bar(
            timestamp=base_time + timedelta(minutes=i),
            open=c - 0.05, high=c + 0.1, low=c - 0.1, close=c, volume=10_000,
        ))
    return bars


class TestMultiTimeframeEngine(unittest.TestCase):
    def test_no_snapshot_defaults_to_neutral_low_confidence(self):
        score = score_multi_timeframe_trend(None, "Bullish")
        self.assertEqual(score.value, 50.0)
        self.assertLess(score.confidence, 0.2)

    def test_aligned_uptrend_across_all_timeframes_scores_high(self):
        rising = _make_bars([10 + i * 0.2 for i in range(20)])
        snapshot = MultiTimeframeSnapshot(
            symbol="TEST",
            series_by_timeframe={tf: TimeframeSeries(timeframe=tf, bars=rising) for tf in ["D", "240", "60", "15", "5", "1"]},
        )
        score = score_multi_timeframe_trend(snapshot, "Bullish")
        self.assertGreater(score.value, 60.0)
        alignment = next(f for f in score.contributing_factors if f.name == "Timeframe Alignment")
        self.assertEqual(alignment.value, 100.0)

    def test_conflicting_timeframes_score_lower_than_aligned(self):
        rising = _make_bars([10 + i * 0.2 for i in range(20)])
        falling = _make_bars([10 - i * 0.2 for i in range(20)])
        mixed_snapshot = MultiTimeframeSnapshot(
            symbol="TEST",
            series_by_timeframe={
                "D": TimeframeSeries(timeframe="D", bars=rising),
                "240": TimeframeSeries(timeframe="240", bars=falling),
                "60": TimeframeSeries(timeframe="60", bars=rising),
                "15": TimeframeSeries(timeframe="15", bars=falling),
            },
        )
        aligned_snapshot = MultiTimeframeSnapshot(
            symbol="TEST",
            series_by_timeframe={tf: TimeframeSeries(timeframe=tf, bars=rising) for tf in ["D", "240", "60", "15"]},
        )
        mixed_score = score_multi_timeframe_trend(mixed_snapshot, "Bullish")
        aligned_score = score_multi_timeframe_trend(aligned_snapshot, "Bullish")
        self.assertLess(mixed_score.value, aligned_score.value)

    def test_partial_timeframe_coverage_reduces_confidence(self):
        rising = _make_bars([10 + i * 0.2 for i in range(20)])
        partial = MultiTimeframeSnapshot(symbol="TEST", series_by_timeframe={"D": TimeframeSeries(timeframe="D", bars=rising)})
        full = MultiTimeframeSnapshot(
            symbol="TEST",
            series_by_timeframe={tf: TimeframeSeries(timeframe=tf, bars=rising) for tf in ["D", "240", "60", "15", "5", "1"]},
        )
        partial_score = score_multi_timeframe_trend(partial, "Bullish")
        full_score = score_multi_timeframe_trend(full, "Bullish")
        self.assertLess(partial_score.confidence, full_score.confidence)

    def test_behavioral_agreement_reflects_confirmed_direction(self):
        rising = _make_bars([10 + i * 0.2 for i in range(20)])
        snapshot = MultiTimeframeSnapshot(symbol="TEST", series_by_timeframe={"D": TimeframeSeries(timeframe="D", bars=rising)})
        bullish_agree = score_multi_timeframe_trend(snapshot, "Bullish")
        bearish_disagree = score_multi_timeframe_trend(snapshot, "Bearish")
        agree_factor = next(f for f in bullish_agree.contributing_factors if f.name == "Behavioral Agreement")
        disagree_factor = next(f for f in bearish_disagree.contributing_factors if f.name == "Behavioral Agreement")
        self.assertGreater(agree_factor.value, disagree_factor.value)


if __name__ == "__main__":
    unittest.main()
