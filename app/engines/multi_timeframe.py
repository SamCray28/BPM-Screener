"""Multi-Timeframe Engine.

Pure functions operating on bar series — genuinely testable with
synthetic data (see tests/unit/test_multi_timeframe.py), unlike the
market data feeding them. When a MultiTimeframeSnapshot has real bars
for Daily/4H/1H/15m/5m/1m (from get_bars() on a real MarketDataProvider),
this produces a real multi-timeframe Trend Score. When timeframes are
missing, it degrades gracefully with reduced confidence rather than
inventing alignment across data it doesn't have.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import Bar, MultiTimeframeSnapshot

_TIMEFRAME_ORDER = ["D", "240", "60", "15", "5", "1"]
_TIMEFRAME_LABELS = {"D": "Daily", "240": "4H", "60": "1H", "15": "15m", "5": "5m", "1": "1m"}


def _bar_direction(bars: List[Bar]) -> str:
    if len(bars) < 2:
        return "Neutral"
    change = bars[-1].close - bars[0].close
    if change > 0:
        return "Bullish"
    if change < 0:
        return "Bearish"
    return "Neutral"


def _persistence_bars(bars: List[Bar]) -> int:
    """Count trailing bars whose close-over-close direction matches the
    most recent bar's direction."""
    if len(bars) < 2:
        return 0
    latest_dir = 1 if bars[-1].close >= bars[-2].close else -1
    count = 0
    for i in range(len(bars) - 1, 0, -1):
        step_dir = 1 if bars[i].close >= bars[i - 1].close else -1
        if step_dir != latest_dir:
            break
        count += 1
    return count


def _acceleration(bars: List[Bar], window: int = 5) -> float:
    """Recent window's average bar-over-bar change vs the prior window's —
    positive means the move is speeding up, negative means slowing."""
    if len(bars) < window * 2:
        return 0.0
    recent = bars[-window:]
    prior = bars[-window * 2:-window]
    recent_change = (recent[-1].close - recent[0].close) / window
    prior_change = (prior[-1].close - prior[0].close) / window
    return recent_change - prior_change


def _exhaustion_score(bars: List[Bar], window: int = 5) -> float:
    """0-100: how much recent bar ranges have shrunk relative to earlier
    ones while price kept moving the same direction — a classic
    exhaustion signature (extension without renewed range expansion)."""
    if len(bars) < window * 2:
        return 0.0
    recent_ranges = [b.high - b.low for b in bars[-window:]]
    prior_ranges = [b.high - b.low for b in bars[-window * 2:-window]]
    recent_avg = sum(recent_ranges) / window
    prior_avg = sum(prior_ranges) / window
    if prior_avg <= 0:
        return 0.0
    shrinkage = max(0.0, 1.0 - (recent_avg / prior_avg))
    return min(100.0, shrinkage * 150.0)


def score_multi_timeframe_trend(
    snapshot: Optional[MultiTimeframeSnapshot],
    confirmed_direction: str,
) -> ScoreExplanation:
    if snapshot is None or not snapshot.series_by_timeframe:
        # Same-session fallback proxy when no multi-timeframe bar data is
        # available at all — capped confidence, never fabricated alignment.
        factors = [EvidenceFactor(
            "Data Availability", 0.0, 1.0,
            "No multi-timeframe bar data supplied for this symbol.",
            "Multi-Timeframe Engine", research_key="Trend Score",
        )]
        return ScoreExplanation(
            score_name="Trend Score", value=50.0, confidence=0.15,
            methodology="No timeframe series available; defaulted to neutral with minimal confidence rather than guessing.",
            contributing_factors=factors, is_original_to_bpm=True,
        )

    directions: Dict[str, str] = {}
    persistence: Dict[str, int] = {}
    acceleration: Dict[str, float] = {}
    exhaustion: Dict[str, float] = {}

    for tf in _TIMEFRAME_ORDER:
        series = snapshot.series_by_timeframe.get(tf)
        if series is None or len(series.bars) < 2:
            continue
        directions[tf] = _bar_direction(series.bars)
        persistence[tf] = _persistence_bars(series.bars)
        acceleration[tf] = _acceleration(series.bars)
        exhaustion[tf] = _exhaustion_score(series.bars)

    available = list(directions.keys())
    if not available:
        factors = [EvidenceFactor(
            "Data Availability", 0.0, 1.0,
            "Timeframe series were supplied but none had enough bars to analyze.",
            "Multi-Timeframe Engine", research_key="Trend Score",
        )]
        return ScoreExplanation(
            score_name="Trend Score", value=50.0, confidence=0.15,
            methodology="Insufficient bars per timeframe; defaulted to neutral.",
            contributing_factors=factors, is_original_to_bpm=True,
        )

    bullish_count = sum(1 for d in directions.values() if d == "Bullish")
    bearish_count = sum(1 for d in directions.values() if d == "Bearish")
    alignment_pct = max(bullish_count, bearish_count) / len(available) * 100.0

    avg_persistence = sum(persistence.values()) / len(persistence)
    persistence_score = min(100.0, avg_persistence * 8.0)

    avg_acceleration = sum(acceleration.values()) / len(acceleration)
    acceleration_score = 50.0 + max(-50.0, min(50.0, avg_acceleration * 500.0))

    avg_exhaustion = sum(exhaustion.values()) / len(exhaustion)
    exhaustion_penalty = avg_exhaustion * 0.3  # exhaustion reduces trend-continuation confidence, doesn't zero it

    behavioral_agreement = 0.0
    if confirmed_direction in ("Bullish", "Bearish"):
        agree_count = sum(1 for d in directions.values() if d == confirmed_direction)
        behavioral_agreement = agree_count / len(available) * 100.0
    else:
        behavioral_agreement = 50.0

    factors = [
        EvidenceFactor("Timeframe Alignment", round(alignment_pct, 1), 0.30,
                        f"{max(bullish_count, bearish_count)}/{len(available)} timeframes "
                        f"({', '.join(_TIMEFRAME_LABELS[t] for t in available)}) agree on direction.",
                        "Auction Market Theory", research_key="Trend Score"),
        EvidenceFactor("Persistence", round(persistence_score, 1), 0.20,
                        f"Average {avg_persistence:.1f} consecutive same-direction bars across analyzed timeframes.",
                        "Market Microstructure", research_key="Trend Score"),
        EvidenceFactor("Acceleration", round(acceleration_score, 1), 0.15,
                        "Recent rate of price change vs. the prior window, averaged across timeframes.",
                        "Market Microstructure", research_key="Trend Score"),
        EvidenceFactor("Exhaustion (inverted)", round(max(0.0, 100.0 - avg_exhaustion), 1), 0.15,
                        f"Average exhaustion signature {avg_exhaustion:.1f}/100 (range shrinkage during continued extension).",
                        "Market Microstructure", research_key="Trend Score"),
        EvidenceFactor("Behavioral Agreement", round(behavioral_agreement, 1), 0.20,
                        f"Share of analyzed timeframes agreeing with Pine's confirmed_direction ('{confirmed_direction}').",
                        "BPM Original", research_key="Trend Score"),
    ]
    value = sum(f.value * f.weight for f in factors) - exhaustion_penalty
    value = max(0.0, min(100.0, value))

    confidence = min(0.9, 0.35 + 0.55 * (len(available) / len(_TIMEFRAME_ORDER)))

    return ScoreExplanation(
        score_name="Trend Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology=(
            "Weighted blend of cross-timeframe alignment, trend persistence, "
            "acceleration, exhaustion (penalizing continuation without renewed "
            "range expansion), and agreement with Pine's confirmed behavioral "
            "direction, computed across whichever of Daily/4H/1H/15m/5m/1m "
            "have sufficient bar data."
        ),
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
