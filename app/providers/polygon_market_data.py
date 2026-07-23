"""Polygon.io market data provider (https://polygon.io/docs/stocks).

Verification status: the parsing functions (`parse_snapshot_ticker`,
`parse_aggregate_bar`) are pure functions tested against realistic mock
JSON shaped like Polygon's documented response format in
tests/providers/test_polygon_market_data_parsing.py — that part is
genuinely verified. The HTTP-fetching methods below have NOT been
exercised against the real Polygon API in this sandbox (no network
access, no API key) — review against current Polygon docs before
relying on this in production; endpoint paths/response shapes can
drift, and I could not confirm today's exact shape live.

Endpoints used (per Polygon's public docs as of my training):
- GET /v2/snapshot/locale/us/markets/stocks/tickers        (universe snapshot)
- GET /v2/snapshot/locale/us/markets/stocks/tickers/{sym}   (single snapshot)
- GET /v2/aggs/ticker/{sym}/range/{mult}/{span}/{from}/{to} (historical bars)
- WSS socket.polygon.io/stocks with {"action":"auth"} then
  {"action":"subscribe","params":"T.SYM,Q.SYM"} (trades + quotes)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.config import Settings
from app.models.snapshot import MarketData, TimeframeSeries
from app.providers.base import MarketDataProvider
from app.providers.http_client import ResilientHttpClient
from app.providers.parsers import parse_aggregate_bar, parse_snapshot_ticker

logger = logging.getLogger("bpm.providers.polygon")

# Pine-style timeframe string -> Polygon (multiplier, timespan)
_TIMEFRAME_MAP = {
    "1": (1, "minute"),
    "5": (5, "minute"),
    "15": (15, "minute"),
    "60": (1, "hour"),
    "240": (4, "hour"),
    "D": (1, "day"),
}


class PolygonMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = ResilientHttpClient(settings, base_url=settings.POLYGON_REST_BASE_URL)

    async def get_universe(self) -> List[MarketData]:
        data = await self._http.get_json(
            "/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"apiKey": self._settings.POLYGON_API_KEY},
        )
        tickers = data.get("tickers", [])
        return [parse_snapshot_ticker(t) for t in tickers]

    async def get_market_data(self, symbol: str) -> MarketData:
        data = await self._http.get_json(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}",
            params={"apiKey": self._settings.POLYGON_API_KEY},
        )
        return parse_snapshot_ticker(data.get("ticker", data))

    async def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> TimeframeSeries:
        if timeframe not in _TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Supported: {sorted(_TIMEFRAME_MAP)}")
        multiplier, timespan = _TIMEFRAME_MAP[timeframe]

        to_date = datetime.now(timezone.utc).date()
        # generous lookback window so `limit` bars are almost always available
        lookback_days = max(5, limit * {"minute": 1, "hour": 1, "day": 3}[timespan])
        from_date = to_date - timedelta(days=lookback_days)

        data = await self._http.get_json(
            f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date.isoformat()}/{to_date.isoformat()}",
            params={"apiKey": self._settings.POLYGON_API_KEY, "limit": limit, "sort": "asc"},
        )
        results = data.get("results", [])
        bars = [parse_aggregate_bar(r) for r in results[-limit:]]
        return TimeframeSeries(timeframe=timeframe, bars=bars)

    async def stream_quotes(self, symbols: List[str]) -> AsyncGenerator[MarketData, None]:
        """Streams live trades/quotes via Polygon's WebSocket feed, with
        automatic reconnect and exponential backoff. Requires the
        `websockets` package. NOT exercised against a live socket in
        this sandbox — no network access here."""
        import websockets  # local import: only needed if streaming is actually used

        backoff = 1.0
        while True:
            try:
                async with websockets.connect(self._settings.POLYGON_WS_URL) as ws:
                    await ws.send(json.dumps({"action": "auth", "params": self._settings.POLYGON_API_KEY}))
                    params = ",".join(f"T.{s}" for s in symbols) + "," + ",".join(f"Q.{s}" for s in symbols)
                    await ws.send(json.dumps({"action": "subscribe", "params": params}))
                    backoff = 1.0  # reset after a successful connect

                    async for raw_message in ws:
                        events = json.loads(raw_message)
                        for event in events if isinstance(events, list) else [events]:
                            market_data = self._event_to_market_data(event)
                            if market_data is not None:
                                yield market_data

            except Exception as exc:  # noqa: BLE001 — must never crash the streaming loop
                logger.warning("Polygon WebSocket disconnected (%s); reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    @staticmethod
    def _event_to_market_data(event: Dict[str, Any]) -> Optional[MarketData]:
        event_type = event.get("ev")
        symbol = event.get("sym")
        if not symbol or event_type not in ("T", "Q"):
            return None
        if event_type == "T":
            return MarketData(
                symbol=symbol, exchange="", last_price=event.get("p", 0.0),
                volume=event.get("s", 0.0), avg_daily_volume=0.0, avg_daily_dollar_volume=0.0,
                timestamp=datetime.fromtimestamp(event.get("t", 0) / 1000.0, tz=timezone.utc),
            )
        return MarketData(
            symbol=symbol, exchange="", last_price=0.0,
            volume=0.0, avg_daily_volume=0.0, avg_daily_dollar_volume=0.0,
            bid=event.get("bp"), ask=event.get("ap"),
            spread=(event.get("ap", 0.0) - event.get("bp", 0.0)) if event.get("ap") and event.get("bp") else None,
            timestamp=datetime.fromtimestamp(event.get("t", 0) / 1000.0, tz=timezone.utc),
        )

    async def aclose(self) -> None:
        await self._http.aclose()
