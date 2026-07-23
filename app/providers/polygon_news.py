"""Polygon.io news provider (https://polygon.io/docs/stocks/get_v2_reference_news).

Same verification split as polygon_market_data.py: `parse_news_article`
(in app/providers/parsers.py) is a pure function tested against
realistic mock JSON; the fetching method itself is unverified against
the live API in this sandbox.
"""
from __future__ import annotations

from typing import List

from app.config import Settings
from app.models.snapshot import NewsItem
from app.providers.base import NewsProvider
from app.providers.http_client import ResilientHttpClient
from app.providers.parsers import parse_news_article


class PolygonNewsProvider(NewsProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = ResilientHttpClient(settings, base_url=settings.POLYGON_REST_BASE_URL)

    async def get_news(self, symbol: str) -> List[NewsItem]:
        data = await self._http.get_json(
            "/v2/reference/news",
            params={"ticker": symbol, "limit": 10, "apiKey": self._settings.POLYGON_API_KEY},
        )
        return [parse_news_article(a, symbol) for a in data.get("results", [])]

    async def aclose(self) -> None:
        await self._http.aclose()
