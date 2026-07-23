from __future__ import annotations

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import MarketData


def score_trend(md: MarketData) -> ScoreExplanation:
    """Single-timeframe proxy only. True multi-timeframe alignment, trend
    persistence/maturity, and exhaustion scoring need higher-timeframe
    series this snapshot does not carry — that's reflected in the capped
    confidence below rather than guessed at."""
    vwap_trend_score = 50.0
    if md.vwap and md.last_price:
        vwap_trend_score = 50.0 + max(-50.0, min(50.0, (md.last_price - md.vwap) / md.vwap * 500.0))
    gap_persistence_score = 0.0 if md.gap_pct is None else min(100.0, abs(md.gap_pct) * 12.0)

    factors = [
        EvidenceFactor("Price vs VWAP", round(vwap_trend_score, 1), 0.6,
                        "Directional position of price relative to VWAP as a same-session trend proxy.",
                        "Auction Market Theory"),
        EvidenceFactor("Gap Persistence", round(gap_persistence_score, 1), 0.4,
                        "Magnitude of the current gap as a proxy for trend initiation strength.",
                        "Market Microstructure"),
    ]
    value = sum(f.value * f.weight for f in factors)

    return ScoreExplanation(
        score_name="Trend Score",
        value=round(value, 1),
        confidence=0.35,  # deliberately capped — see docstring
        methodology=(
            "Single-timeframe proxy for trend using price-vs-VWAP position "
            "and gap persistence. This is a partial substitute for true "
            "multi-timeframe alignment/persistence/maturity analysis, which "
            "requires higher-timeframe data feeds not present in this "
            "snapshot — confidence is capped accordingly rather than "
            "presented as complete trend analysis."
        ),
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
