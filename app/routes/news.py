from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.providers.factory import build_news_provider

router = APIRouter(prefix="/news", tags=["news"])


class NewsItemOut(BaseModel):
    timestamp: str
    source: str
    headline: str
    summary: str
    relevance: float
    estimated_behavioral_impact: str
    confidence: float
    freshness_hours: float | None = None
    source_reliability: float | None = None


@router.get("/{symbol}", response_model=List[NewsItemOut])
async def get_news(symbol: str, settings: Settings = Depends(get_settings)) -> List[NewsItemOut]:
    provider = build_news_provider(settings)
    items = await provider.get_news(symbol.upper())
    return [
        NewsItemOut(
            timestamp=item.timestamp.isoformat(), source=item.source, headline=item.headline,
            summary=item.summary, relevance=item.relevance,
            estimated_behavioral_impact=item.estimated_behavioral_impact, confidence=item.confidence,
            freshness_hours=item.freshness_hours, source_reliability=item.source_reliability,
        )
        for item in items
    ]
