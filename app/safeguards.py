"""Cross-cutting invariants the spec treats as non-negotiable:

- The screener must never emit a directional trading instruction
  (BUY/SELL/LONG/SHORT).
- Every score reaching a user must carry a full explanation.

ScoreExplanation already enforces the second rule structurally at
construction time (see app/models/evidence.py). assert_explained here
is a defensive re-check at the ranking boundary, in case a future
engine builds a ScoreExplanation-like object a different way.

Known limitation: assert_no_directional_language does a literal
word-boundary scan for "buy", "sell", "long", "short". That correctly
catches the trading-instruction sense the spec is worried about, but
it will also flag ordinary English uses of "long" and "short" (e.g.
"long-term", "short window") if such words are ever introduced into a
generated template. The engines in this codebase are written to avoid
those words entirely for exactly this reason. If you extend the
templates, prefer "extended"/"brief" over "long"/"short", or refine
this check to look for instruction phrasing specifically before
loosening it.
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
    """Run every output-facing string through the directional-language
    check, and every score through the explainability check, before it
    is allowed to reach a user."""
    for score in [ranked.overall_score, *ranked.sub_scores]:
        assert_explained(score)

    text_fields: Iterable[str] = [
        ranked.behavioral_context,
        *(ranked.supporting_evidence or []),
        *(ranked.primary_risks or []),
        *(ranked.reasons_for_ranking or []),
        ranked.historical_expectancy or "",
        ranked.capital_efficiency or "",
        ranked.estimated_hold_duration or "",
    ]
    for text in text_fields:
        if text:
            assert_no_directional_language(text, context=f"{ranked.symbol} output")
