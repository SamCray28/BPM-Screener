"""In-memory holder for the most recent ranking run. The scheduler
(app/scheduler.py) recomputes and stores here every RANKING_REFRESH_SECONDS;
routes read from here rather than recomputing per-request. Persisted
history lives in the ranking_runs/ranking_results tables (see
app/models/db_models.py) — this is just the fast-path cache for "what's
current right now"."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.models.ranking import RankedSymbol


class RankingCache:
    def __init__(self) -> None:
        self._results: List[RankedSymbol] = []
        self._updated_at: Optional[datetime] = None

    def set(self, results: List[RankedSymbol]) -> None:
        self._results = results
        self._updated_at = datetime.now(timezone.utc)

    def get(self) -> List[RankedSymbol]:
        return self._results

    def get_for_symbol(self, symbol: str) -> Optional[RankedSymbol]:
        for r in self._results:
            if r.symbol == symbol:
                return r
        return None

    @property
    def updated_at(self) -> Optional[datetime]:
        return self._updated_at


ranking_cache = RankingCache()
