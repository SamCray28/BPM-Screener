from __future__ import annotations

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import MarketData


def score_capital_efficiency(md: MarketData) -> ScoreExplanation:
    """How much room a behavioral move has relative to what it costs to
    enter/exit — spread and ATR as execution-cost proxies. Says nothing
    about position sizing or portfolio risk, which remain the user's
    own decisions."""
    if md.spread is None or md.atr is None or md.atr == 0:
        factors = [EvidenceFactor("Data Availability", 0.0, 1.0,
                                   "Spread and/or ATR not available for this symbol.",
                                   "Market Microstructure", research_key="Capital Efficiency Score")]
        return ScoreExplanation(
            score_name="Capital Efficiency Score", value=50.0, confidence=0.2,
            methodology="Insufficient market data; defaulted to neutral.",
            contributing_factors=factors,
        )

    spread_to_atr = md.spread / md.atr
    efficiency = max(0.0, min(100.0, 100.0 - spread_to_atr * 200.0))

    rvol_bonus = 0.0
    if md.relative_volume is not None:
        rvol_bonus = min(20.0, max(0.0, (md.relative_volume - 1.0) * 10.0))

    value = min(100.0, efficiency + rvol_bonus)

    factors = [
        EvidenceFactor("Spread-to-ATR Ratio", round(efficiency, 1), 0.8,
                        f"Spread ({md.spread:.4f}) as a fraction of ATR ({md.atr:.4f}) — lower is more capital-efficient.",
                        "Market Microstructure", research_key="Capital Efficiency Score"),
        EvidenceFactor("Relative Volume Bonus", round(rvol_bonus, 1), 0.2,
                        "Elevated relative volume typically improves fill quality relative to the static spread/ATR ratio.",
                        "Market Microstructure", research_key="Capital Efficiency Score"),
    ]

    return ScoreExplanation(
        score_name="Capital Efficiency Score",
        value=round(value, 1),
        confidence=0.75,
        methodology="Spread-to-ATR ratio (execution cost relative to typical move size), adjusted by a relative-volume bonus.",
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
