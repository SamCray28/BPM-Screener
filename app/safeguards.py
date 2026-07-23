"""Cross-cutting invariants:

- The platform must never emit a directional trading instruction
  (BUY/SELL/LONG/SHORT) — RankedSymbol has no field for one, and every
  output-facing string is scanned defensively before it can be returned.
- Every score reaching a user must carry a full explanation (also
  enforced structurally by ScoreExplanation.__post_init__).

Known limitation: the language scan is a literal word-boundary match on
{buy, sell, long, short}. It will also flag ordinary English uses of
"long"/"short" (e.g. "long-term") if those words are ever introduced
into a generated template — every engine in this codebase avoids them
for exactly this reason. SEC Form 4 filings genuinely use "Buy"/"Sell"
as category labels; see describe_insider_transaction() in
app/models/snapshot.py for how that's neutralized before it can reach
output text.
"""
from __future__ import annotations

import re
from typing import Iterable

from app.models.evidence import ScoreExplanation
from app.models.ranking import RankedSymbol

_FORBIDDEN_TERMS = ("buy", "sell", "long", "short")
_WORD_RE = re.compile(r"[a-zA-Z]+")


class DirectionalLanguageError(ValueError):
    pass


class UnexplainedScoreError(ValueError):
    pass


def assert_no_directional_language(text: str, context: str = "") -> None:
    words = {w.lower() for w in _WORD_RE.findall(text)}
    hit = words.intersection(_FORBIDDEN_TERMS)
    if hit:
        raise DirectionalLanguageError(
            f"Forbidden directional term(s) {sorted(hit)} found in {context or 'output'}: {text!r}"
        )


def assert_explained(score: ScoreExplanation) -> None:
    if not score.contributing_factors:
        raise UnexplainedScoreError(f"{score.score_name} has no contributing factors — cannot be displayed.")
    if not score.methodology or not score.methodology.strip():
        raise UnexplainedScoreError(f"{score.score_name} has no methodology — cannot be displayed.")


def validate_ranked_symbol(ranked: RankedSymbol) -> None:
    for score in [ranked.behavior_score, ranked.opportunity_score, *ranked.sub_scores]:
        assert_explained(score)

    text_fields: Iterable[str] = [
        ranked.behavior_state,
        ranked.acceptance,
        ranked.trend_summary,
        ranked.liquidity_summary,
        *(ranked.recent_news or []),
        *(ranked.primary_risks or []),
        *(ranked.reasons_for_ranking or []),
        *(ranked.supporting_evidence or []),
        ranked.historical_expectancy or "",
        ranked.estimated_hold_duration or "",
        ranked.capital_efficiency or "",
    ]
    for text in text_fields:
        if text:
            assert_no_directional_language(text, context=f"{ranked.symbol} output")
