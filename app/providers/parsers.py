"""Pure parsing functions for every real provider's response format.
Deliberately zero third-party imports (no httpx, no pydantic) so these
can be unit-tested in any environment, including one with no
dependencies installed — see tests/unit/test_provider_parsers.py, which
genuinely exercises every function here against realistic mock JSON.

The provider classes (polygon_market_data.py, polygon_news.py,
finnhub_corporate_events.py, sec_edgar_filings.py) import from this
module rather than defining parsing inline.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.models.snapshot import (
    AnalystRevision,
    Bar,
    EarningsEvent,
    InsiderTransaction,
    MarketData,
    NewsItem,
    SECFiling,
)

# --- Polygon.io market data --------------------------------------------------

_SENTIMENT_TO_IMPACT = {"positive": "Supportive", "negative": "Conflicting", "neutral": "Neutral"}


def parse_snapshot_ticker(raw: Dict[str, Any]) -> MarketData:
    day = raw.get("day") or {}
    prev_day = raw.get("prevDay") or {}
    last_trade = raw.get("lastTrade") or {}
    last_quote = raw.get("lastQuote") or {}

    last_price = last_trade.get("p") or day.get("c") or 0.0
    prev_close = prev_day.get("c")
    day_open = day.get("o")
    high = day.get("h")
    low = day.get("l")
    volume = day.get("v") or 0.0
    vwap = day.get("vw")

    bid = last_quote.get("p")
    ask = last_quote.get("P")
    spread = (ask - bid) if (bid is not None and ask is not None) else None

    gap_pct = None
    if prev_close and day_open:
        gap_pct = (day_open - prev_close) / prev_close * 100.0

    daily_range = (high - low) if (high is not None and low is not None) else None

    updated_ns = raw.get("updated")
    timestamp = datetime.fromtimestamp(updated_ns / 1_000_000_000, tz=timezone.utc) if updated_ns else None

    return MarketData(
        symbol=raw.get("ticker", ""),
        exchange=raw.get("primary_exchange", raw.get("exchange", "")),
        last_price=float(last_price),
        volume=float(volume),
        avg_daily_volume=float(volume),
        avg_daily_dollar_volume=float(volume) * float(last_price),
        timestamp=timestamp,
        bid=bid, ask=ask, spread=spread,
        relative_volume=None, vwap=vwap, atr=None, daily_range=daily_range, gap_pct=gap_pct,
        halt_status=None,
    )


def parse_aggregate_bar(raw: Dict[str, Any]) -> Bar:
    return Bar(
        timestamp=datetime.fromtimestamp(raw["t"] / 1000.0, tz=timezone.utc),
        open=raw["o"], high=raw["h"], low=raw["l"], close=raw["c"], volume=raw["v"],
    )


def parse_news_article(raw: Dict[str, Any], symbol: str) -> NewsItem:
    published = raw.get("published_utc")
    timestamp = (
        datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)
    )
    freshness_hours = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600.0

    impact = "Neutral"
    confidence = 0.3
    for insight in raw.get("insights", []) or []:
        if insight.get("ticker") == symbol and insight.get("sentiment"):
            impact = _SENTIMENT_TO_IMPACT.get(insight["sentiment"].lower(), "Neutral")
            confidence = 0.75
            break

    publisher = (raw.get("publisher") or {}).get("name", "Unknown")

    return NewsItem(
        timestamp=timestamp, source=publisher, headline=raw.get("title", ""), summary=raw.get("description", ""),
        relevance=1.0 if symbol in (raw.get("tickers") or []) else 0.5,
        estimated_behavioral_impact=impact, confidence=confidence,
        freshness_hours=round(freshness_hours, 2), source_reliability=None,
    )


# --- Finnhub corporate events -------------------------------------------------

_TRANSACTION_CODE_MAP = {"P": "Buy", "S": "Sell"}
_ACTION_MAP = {"up": "Upgrade", "down": "Downgrade", "init": "Initiate", "main": "Reiterate"}


def parse_earnings_event(raw: Dict[str, Any]) -> EarningsEvent:
    period = raw.get("period")
    timestamp = datetime.fromisoformat(period) if period else datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return EarningsEvent(
        timestamp=timestamp,
        eps_actual=raw.get("actual"), eps_estimate=raw.get("estimate"), surprise_pct=raw.get("surprisePercent"),
        reaction_pct=None,
    )


def parse_insider_transaction(raw: Dict[str, Any]) -> InsiderTransaction:
    code = raw.get("transactionCode", "")
    txn_type = _TRANSACTION_CODE_MAP.get(code, "Other")
    txn_date = raw.get("transactionDate") or raw.get("filingDate")
    timestamp = (
        datetime.fromisoformat(txn_date).replace(tzinfo=timezone.utc) if txn_date else datetime.now(timezone.utc)
    )
    return InsiderTransaction(
        timestamp=timestamp, insider_role=raw.get("name", "Unknown"), transaction_type=txn_type,
        shares=raw.get("share"),
        value_estimate=(raw.get("share", 0.0) * raw.get("transactionPrice", 0.0))
        if raw.get("share") and raw.get("transactionPrice") else None,
    )


def parse_analyst_revision(raw: Dict[str, Any]) -> AnalystRevision:
    grade_time = raw.get("gradeTime")
    timestamp = datetime.fromtimestamp(grade_time, tz=timezone.utc) if grade_time else datetime.now(timezone.utc)
    return AnalystRevision(
        timestamp=timestamp, firm=raw.get("company", "Unknown"),
        action=_ACTION_MAP.get(raw.get("action", ""), "Reiterate"), price_target=None,
    )


# --- SEC EDGAR filings ---------------------------------------------------------

def parse_recent_filings(raw: Dict[str, Any], limit: int = 10) -> List[SECFiling]:
    recent = (raw.get("filings") or {}).get("recent") or {}
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    cik = str(raw.get("cik", "")).lstrip("0")

    filings: List[SECFiling] = []
    for i in range(min(limit, len(forms))):
        accession = accession_numbers[i].replace("-", "") if i < len(accession_numbers) else ""
        doc = primary_documents[i] if i < len(primary_documents) else ""
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
            if cik and accession and doc else None
        )
        filings.append(SECFiling(
            timestamp=datetime.fromisoformat(dates[i]) if i < len(dates) else datetime.now(),
            filing_type=forms[i],
            headline=f"{forms[i]} filed {dates[i] if i < len(dates) else ''}",
            url=url,
        ))
    return filings
