from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter

from app.ranking_cache import ranking_cache

router = APIRouter(tags=["statistics"])


class StatisticsOut(BaseModel):
    universe_size: int
    last_updated: str | None
    average_opportunity_score: float | None
    average_confidence: float | None
    symbols_with_sufficient_history: int


@router.get("/statistics", response_model=StatisticsOut)
def statistics() -> StatisticsOut:
    results = ranking_cache.get()
    if not results:
        return StatisticsOut(
            universe_size=0, last_updated=None, average_opportunity_score=None,
            average_confidence=None, symbols_with_sufficient_history=0,
        )
    avg_opportunity = sum(r.opportunity_score.value for r in results) / len(results)
    avg_confidence = sum(r.confidence for r in results) / len(results)
    sufficient_history = sum(1 for r in results if (r.historical_sample_size or 0) > 0 and r.historical_expectancy)

    return StatisticsOut(
        universe_size=len(results),
        last_updated=ranking_cache.updated_at.isoformat() if ranking_cache.updated_at else None,
        average_opportunity_score=round(avg_opportunity, 2),
        average_confidence=round(avg_confidence, 2),
        symbols_with_sufficient_history=sufficient_history,
    )
