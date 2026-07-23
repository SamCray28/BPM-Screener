"""Tests for app/providers/parsers.py — the pure parsing functions
behind the Polygon, Finnhub, and SEC EDGAR providers. Mock JSON below
is shaped to match each vendor's documented response format as best I
can recall it; it has not been diffed against a live API response in
this sandbox (no network access), so treat this as "the parser handles
the documented shape correctly," not "confirmed against today's live
API output."
"""
import unittest

from app.providers.parsers import (
    parse_aggregate_bar,
    parse_analyst_revision,
    parse_earnings_event,
    parse_insider_transaction,
    parse_news_article,
    parse_recent_filings,
    parse_snapshot_ticker,
)


class TestPolygonMarketDataParsing(unittest.TestCase):
    def test_parse_snapshot_ticker_basic_fields(self):
        raw = {
            "ticker": "ALPH",
            "primary_exchange": "XNAS",
            "day": {"o": 10.0, "h": 10.8, "l": 9.7, "c": 10.5, "v": 1_200_000, "vw": 10.2},
            "prevDay": {"c": 9.8},
            "lastTrade": {"p": 10.55, "s": 100, "t": 1_700_000_000_000_000_000},
            "lastQuote": {"p": 10.54, "P": 10.56, "s": 2, "S": 3},
            "updated": 1_700_000_000_000_000_000,
        }
        md = parse_snapshot_ticker(raw)
        self.assertEqual(md.symbol, "ALPH")
        self.assertAlmostEqual(md.last_price, 10.55)
        self.assertAlmostEqual(md.bid, 10.54)
        self.assertAlmostEqual(md.ask, 10.56)
        self.assertAlmostEqual(md.spread, 0.02, places=6)
        self.assertAlmostEqual(md.daily_range, 1.1, places=6)
        self.assertIsNotNone(md.gap_pct)
        self.assertIsNotNone(md.timestamp)

    def test_parse_snapshot_ticker_handles_missing_optional_fields(self):
        raw = {"ticker": "BETA", "day": {"c": 5.0, "v": 100}}
        md = parse_snapshot_ticker(raw)
        self.assertEqual(md.symbol, "BETA")
        self.assertIsNone(md.bid)
        self.assertIsNone(md.spread)
        self.assertIsNone(md.gap_pct)

    def test_parse_aggregate_bar(self):
        raw = {"t": 1_700_000_000_000, "o": 10.0, "h": 10.5, "l": 9.8, "c": 10.2, "v": 5000}
        bar = parse_aggregate_bar(raw)
        self.assertEqual(bar.open, 10.0)
        self.assertEqual(bar.close, 10.2)
        self.assertEqual(bar.volume, 5000)


class TestPolygonNewsParsing(unittest.TestCase):
    def test_parse_news_article_with_insight_sentiment(self):
        raw = {
            "published_utc": "2026-07-20T12:00:00Z",
            "publisher": {"name": "Example Wire"},
            "title": "ALPH announces expansion",
            "description": "Sample description.",
            "tickers": ["ALPH"],
            "insights": [{"ticker": "ALPH", "sentiment": "positive"}],
        }
        item = parse_news_article(raw, "ALPH")
        self.assertEqual(item.estimated_behavioral_impact, "Supportive")
        self.assertEqual(item.relevance, 1.0)
        self.assertGreaterEqual(item.confidence, 0.7)

    def test_parse_news_article_without_insight_defaults_neutral(self):
        raw = {"published_utc": "2026-07-20T12:00:00Z", "publisher": {"name": "X"}, "title": "t", "tickers": ["OTHER"]}
        item = parse_news_article(raw, "ALPH")
        self.assertEqual(item.estimated_behavioral_impact, "Neutral")
        self.assertEqual(item.relevance, 0.5)  # symbol not in tickers list


class TestFinnhubParsing(unittest.TestCase):
    def test_parse_earnings_event(self):
        raw = {"period": "2026-06-30", "actual": 1.25, "estimate": 1.10, "surprisePercent": 13.6}
        event = parse_earnings_event(raw)
        self.assertEqual(event.eps_actual, 1.25)
        self.assertEqual(event.surprise_pct, 13.6)

    def test_parse_insider_transaction_buy_code(self):
        raw = {
            "name": "Jane Smith", "transactionCode": "P", "transactionDate": "2026-07-01",
            "share": 1000, "transactionPrice": 12.5,
        }
        txn = parse_insider_transaction(raw)
        self.assertEqual(txn.transaction_type, "Buy")
        self.assertEqual(txn.value_estimate, 12500.0)

    def test_parse_insider_transaction_sell_code(self):
        raw = {"name": "John Doe", "transactionCode": "S", "transactionDate": "2026-07-01", "share": 500}
        txn = parse_insider_transaction(raw)
        self.assertEqual(txn.transaction_type, "Sell")

    def test_parse_insider_transaction_unknown_code_maps_to_other(self):
        raw = {"name": "Someone", "transactionCode": "A", "filingDate": "2026-07-01"}
        txn = parse_insider_transaction(raw)
        self.assertEqual(txn.transaction_type, "Other")

    def test_parse_analyst_revision_action_mapping(self):
        raw = {"gradeTime": 1_700_000_000, "company": "Sample Capital", "action": "up"}
        rev = parse_analyst_revision(raw)
        self.assertEqual(rev.action, "Upgrade")
        self.assertEqual(rev.firm, "Sample Capital")


class TestSecEdgarParsing(unittest.TestCase):
    def test_parse_recent_filings_column_oriented_json(self):
        raw = {
            "cik": "0000320193",
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K"],
                    "filingDate": ["2026-02-01", "2026-05-15"],
                    "accessionNumber": ["0000320193-26-000010", "0000320193-26-000042"],
                    "primaryDocument": ["a10k.htm", "a8k.htm"],
                }
            },
        }
        filings = parse_recent_filings(raw)
        self.assertEqual(len(filings), 2)
        self.assertEqual(filings[0].filing_type, "10-K")
        self.assertIn("320193", filings[0].url)
        self.assertTrue(filings[0].url.endswith("a10k.htm"))

    def test_parse_recent_filings_handles_empty(self):
        filings = parse_recent_filings({"cik": "1", "filings": {"recent": {}}})
        self.assertEqual(filings, [])


if __name__ == "__main__":
    unittest.main()
