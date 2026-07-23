# BPM Behavioral Intelligence Screener (BIS) — v0.1.0

## Read this first

The BIS spec describes an institutional-grade, real-time screener across
the entire NYSE/NASDAQ/AMEX universe, with live market data, live news
and SEC-filing ingestion, a continuously growing historical trade
database, options positioning, and institutional-participation
estimates.

**This sandbox has no network access and no market-data, news, or
broker credentials.** Nothing here connects to a real feed, and nothing
here should be mistaken for one. What's implemented instead is the part
that's actually deliverable without those things: the decision-support
*architecture* the spec demands — explainability, provider-agnostic
interfaces, every scoring engine, and the ranking pipeline — proven out
end-to-end against synthetic data, with the spec's non-negotiable rules
enforced *in code*, not just described.

All 13 unit tests pass and `examples/run_demo.py` runs end-to-end in
this environment right now (pure standard library — no dependencies to
install). Try it:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 examples/run_demo.py
```

## What's actually enforced in code (not just claimed)

- **Rule 2 (Explainability)** — `ScoreExplanation` (`app/models/evidence.py`)
  refuses to even construct if it has no contributing factors or no
  methodology string. A score with nothing behind it cannot exist in
  this system, let alone be displayed.
- **Rule 1 / final governing rule (evidence over invented certainty)** —
  `score_historical()` (`app/engines/historical.py`) hard-gates on
  `HistoricalConfig.min_sample_size`: below the threshold, the score's
  *value and confidence both go to zero* rather than showing a
  win-rate/expectancy number that looks precise but isn't supported.
  The Behavior Score's Forecast Reliability sub-factor applies the same
  rule to Pine's forecast bias specifically (see below).
- **"Never BUY/SELL/LONG/SHORT"** — `app/safeguards.py` scans every
  output-facing string in a `RankedSymbol` for those terms before
  `build_ranking()` will return it; `RankedSymbol` also simply has no
  field for a directional instruction. This got a real test: SEC Form 4
  filings genuinely categorize insider transactions as "Buy"/"Sell" —
  `describe_insider_transaction()` in `app/models/snapshot.py` translates
  those into neutral language ("an acquisition"/"a disposition") before
  they can reach any output field, and
  `tests/test_insider_transaction_language.py` proves both directions
  pass the safeguard cleanly.
- **Rule 3 (label BPM-original metrics as such)** — every
  `ScoreExplanation` and every `ResearchCard` carries `is_original_to_bpm`.
- **BPM stays the source of truth for behavior** — `BehavioralData`
  mirrors the Pine telemetry fields exactly (see the `bpm-python`
  receiver's `TelemetryIn`); nothing here recomputes BO/MC/state.

## Behavioral Science Layer — the 7-factor Behavior Score

`score_behavioral()` (`app/engines/behavioral.py`) no longer returns a
bare number. It returns a `ScoreExplanation` whose `contributing_factors`
are exactly:

| Factor | Weight | Source |
|---|---|---|
| Acceptance | 22% | Pine's `acceptance_status` |
| Pressure | 18% | Pine's `pressure_efficiency` |
| Structure | 19% | Pine's `confirmed_state` + `bo_status` + `mc_status` |
| Forecast Reliability | 14% | Pine's `forecast_bias` × Behavioral Database sample depth |
| Behavioral Stability | 9% | `bars_in_confirmed_state` (requires the Behavioral Database) |
| Transition Risk | 8% | Heuristic, displayed inverted (higher = lower risk) — see limitation below |
| Historical Similarity | 10% | Behavioral Database occurrence count for this exact condition |

Weights sum to exactly 1.00 (`tests/test_behavior_score_decomposition.py`
checks this). Three of the seven factors (Forecast Reliability,
Behavioral Stability, Historical Similarity) only reach a meaningful
value once the Behavioral Database below is populated — until then they
correctly default to low-confidence neutral values instead of guessing.
Transition Risk is currently a documented heuristic, not yet backed by
real transition-frequency statistics (see its Research Card).

## Research Engine

`app/research.py` defines a `ResearchCard` for every sub-factor and
every top-level score: Definition / Research Basis / Calculation /
Evidence / Confidence Notes / Limitations / `is_original_to_bpm` — the
exact shape you asked for. `EvidenceFactor` now carries a `research_key`
so any UI can go from "why did Pressure score 58" straight to its card.

Two honesty constraints this module follows (stated up front in its
own docstring, not buried): it never fabricates specific empirical
findings or citations it can't verify — research basis names
established fields and, where genuinely famous and uncontroversial,
the associated theory (Kahneman & Tversky's Prospect Theory, Kyle's
market-impact model, Steidlmayer's Auction Market Theory) — and its
`evidence` field describes what evidence exists *in this build*
(currently: none beyond direct Pine reads and synthetic mock data),
not invented backtest statistics.

## Behavioral Database (`app/db/`)

Schema (`app/db/models.py`, SQLAlchemy 2.x) for exactly the pieces you
listed: `BehavioralSnapshot`, `TradeOutcome`, `BehavioralTransition`,
`ForecastRecord`, `AcceptanceEvent`, `PressureBurstEvent`,
`EarningsEventRecord`, `NewsCatalystRecord`. `BehavioralSnapshot` is the
spine; everything else links to it by `snapshot_id` or by
`symbol`+timestamp.

`app/db/repositories.py` includes `SQLAlchemyHistoricalStatsProvider` —
a real implementation of `HistoricalStatsProvider` that queries this
schema and returns the exact `HistoricalStats` shape
`score_historical()` and `score_behavioral()` already consume. Swap it
in for `MockHistoricalStatsProvider` once the database has real rows
and every downstream score starts working from actual evidence with
zero other code changes.

**This file is syntax-checked only** (`py_compile`), not executed
against a real database — no network access in this sandbox to install
SQLAlchemy or connect to Postgres. It's designed to plausibly share
infrastructure with the already-deployed `bpm-python` receiver (same
Postgres instance, consistent ORM style).

## Institutional Data Layer additions

Added `CorporateEventsProvider` (`app/providers/base.py`) with four
methods: `get_sec_filings`, `get_earnings_events`,
`get_insider_transactions`, `get_analyst_revisions`, plus
`MockCorporateEventsProvider` for the demo. These currently feed into
`build_ranking()`'s `supporting_evidence`/`primary_risks` text, not a
dedicated new score — folding them into a proper Catalyst Score
(instead of ranking-engine text) is the natural next step if you want
that data to carry ranking weight rather than just context.

Level II and options flow are not implemented — you marked both
"(future)" yourself, and neither has a settled interface here yet.

## Project layout

```
app/
  config.py              UniverseConfig, HistoricalConfig, ScoringWeights
  safeguards.py           Directional-language + explainability enforcement
  research.py             Research Engine — ResearchCard registry
  models/
    evidence.py            EvidenceFactor (+research_key), ScoreExplanation
    snapshot.py             MarketData, BehavioralData, NewsItem, HistoricalStats,
                             SECFiling, EarningsEvent, InsiderTransaction, AnalystRevision
    ranking.py              RankedSymbol (the Decision Output shape)
  providers/
    base.py                 5 abstract interfaces — implement these for real data
    mock_provider.py         Synthetic demo data ONLY — not real market/news/filing data
  engines/
    universe.py             Price/exchange/liquidity filtering
    behavioral.py            Behavior Score (7-factor decomposition)
    market_structure.py      Market Structure Score
    liquidity.py             Liquidity Score
    historical.py            Historical Confidence Score (sample-gated)
    trend.py                 Trend Score (single-timeframe proxy — see docstring)
    sentiment.py             News Impact Score
    scoring.py               Overall Behavioral Opportunity Score
    ranking.py               Assembles the full Decision Output per symbol
  db/
    models.py                Behavioral Database schema (SQLAlchemy, compile-checked only)
    repositories.py           Query layer + SQLAlchemyHistoricalStatsProvider
tests/                       22 tests, all passing, pure stdlib unittest
examples/run_demo.py         Runs the whole pipeline end-to-end on mock data
```

## What is genuinely NOT implemented (and why)

| Spec requirement | Status | What it needs |
|---|---|---|
| Live/near-real-time market data (last trade, bid/ask, order flow, Time & Sales) | Not implemented | A real market data vendor (e.g. Polygon, IEX, Databento) — implement `MarketDataProvider` |
| Full market universe scan (all NYSE/NASDAQ/AMEX under $50) | Not implemented | Same — the universe filter logic exists (`engines/universe.py`), it just has no real universe to filter yet |
| News/SEC filings/analyst actions engine | Not implemented | A news/filings API (e.g. Benzinga, a SEC EDGAR feed) — implement `NewsProvider` |
| Continuously growing historical trade database with real win rate/R-multiples/MFE/MAE | Not implemented | A real trade/outcome journal or backtest database — implement `HistoricalStatsProvider`; the gating and scoring logic are ready for it |
| True multi-timeframe trend (alignment, persistence, maturity, exhaustion) | Partial | `score_trend()` is an honest single-timeframe VWAP/gap proxy with confidence capped at 0.35 specifically because it isn't the real thing — needs higher-timeframe series |
| Sentiment beyond news (social sentiment, options positioning, institutional accumulation proxies) | Not implemented | Spec itself lists options positioning as "future module" — social/options data sources |
| Behavioral Transition Probability, Historical Similarity, Forecast Confidence as calibrated probabilities | Not implemented | These require actual historical calibration (the Pine script's own doctrine says the same thing: a raw score is not a probability until it's been calibrated against historical research) |

## Extending to real data

Implement the four ABCs in `app/providers/base.py` against real vendors.
Nothing in `app/engines` or `app/models` needs to change — that's the
entire point of the provider-agnostic boundary the spec asked for.
