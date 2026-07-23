"""Rule-based sentiment classifier. This is a deliberately simple
keyword-weighted heuristic, not a trained NLP model — real social/
options-flow sentiment (per the spec's Sentiment Engine section) needs
a real vendor (e.g. a social-listening API or options-flow provider),
which is out of scope here. This exists so SentimentProvider has at
least one honest, fully-tested implementation rather than only a mock.
"""
from __future__ import annotations

import re
from typing import Tuple

from app.providers.base import SentimentProvider

_POSITIVE_TERMS = {
    "beat", "beats", "surge", "record", "growth", "upgraded", "outperform",
    "strong", "expansion", "raises", "exceeds", "positive",
}
_NEGATIVE_TERMS = {
    "miss", "misses", "plunge", "decline", "downgraded", "underperform",
    "weak", "compression", "cuts", "lawsuit", "investigation", "negative",
    "recall", "halted",
}

_WORD_RE = re.compile(r"[a-zA-Z]+")


class RuleBasedSentimentProvider(SentimentProvider):
    async def classify_text(self, text: str) -> Tuple[str, float]:
        words = [w.lower() for w in _WORD_RE.findall(text)]
        pos_hits = sum(1 for w in words if w in _POSITIVE_TERMS)
        neg_hits = sum(1 for w in words if w in _NEGATIVE_TERMS)

        if pos_hits == 0 and neg_hits == 0:
            return "Neutral", 0.2  # low confidence — no signal either way

        total = pos_hits + neg_hits
        if pos_hits > neg_hits:
            return "Positive", min(0.9, 0.4 + 0.15 * total)
        if neg_hits > pos_hits:
            return "Negative", min(0.9, 0.4 + 0.15 * total)
        return "Neutral", 0.35  # tied signals
