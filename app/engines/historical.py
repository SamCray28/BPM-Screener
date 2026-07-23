from __future__ import annotations

from typing import Optional

from app.config import HistoricalConfig
from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import HistoricalStats


def score_historical(stats: Optional[HistoricalStats], config: HistoricalConfig) -> ScoreExplanation:
    occurrences = stats.occurrences if stats else 0
    sufficient = occurrences >= config.min_sample_size

    if not sufficient or stats is None or stats.win_rate is None:
        # "No probability should be displayed below a configurable minimum
        # sample threshold" — the score itself goes to zero value/zero
        # confidence rather than showing a number that looks precise but
        # isn't supported by enough evidence.
        factors = [
            EvidenceFactor(
                "Sample Sufficiency", 0.0, 1.0,
                f"Only {occurrences} historical occurrence(s) found; "
                f"{config.min_sample_size} required before any win-rate or "
                f"expectancy figure is displayed.",
                "Historical Engine",
            )
        ]
        return ScoreExplanation(
            score_name="Historical Confidence Score",
            value=0.0,
            confidence=0.0,
            methodology="Sample size gate: below the configured minimum, no probability is computed or shown.",
            contributing_factors=factors,
            sample_size=occurrences,
            historical_support="Insufficient sample — no historical probability available.",
        )

    win_rate_score = stats.win_rate * 100.0
    pf_score = 0.0 if stats.profit_factor is None else min(100.0, stats.profit_factor / 2.5 * 100.0)
    sample_score = min(100.0, (occurrences / (config.min_sample_size * 3)) * 100.0)

    factors = [
        EvidenceFactor("Historical Win Rate", round(win_rate_score, 1), 0.45,
                        f"{stats.win_rate:.0%} win rate across {occurrences} tracked occurrences.",
                        "Historical Engine"),
        EvidenceFactor(
            "Profit Factor", round(pf_score, 1), 0.35,
            f"Profit factor of {stats.profit_factor:.2f}." if stats.profit_factor else "No profit factor recorded.",
            "Historical Engine",
        ),
        EvidenceFactor("Sample Depth", round(sample_score, 1), 0.20,
                        f"{occurrences} occurrences tracked (minimum required: {config.min_sample_size}).",
                        "Historical Engine"),
    ]
    value = sum(f.value * f.weight for f in factors)
    # Confidence grows with sample size but is capped — more data helps,
    # but this one component should never claim full certainty on its own.
    confidence = min(0.95, 0.4 + 0.55 * min(1.0, occurrences / (config.min_sample_size * 4)))

    ci_text = None
    if stats.confidence_interval_95:
        lo, hi = stats.confidence_interval_95
        ci_text = f"95% CI on win rate: [{lo:.0%}, {hi:.0%}] (n={occurrences})."

    return ScoreExplanation(
        score_name="Historical Confidence Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology=(
            "Weighted combination of historical win rate, profit factor, and "
            "sample depth for this specific behavioral condition, gated by a "
            "minimum sample size before any figure is shown."
        ),
        contributing_factors=factors,
        sample_size=occurrences,
        historical_support=ci_text,
    )
