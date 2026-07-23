# BPM Behavioral Intelligence Platform — v4.0.0

Python backend for BPM: receives TradingView's behavioral telemetry,
combines it with market structure, liquidity, historical statistics,
multi-timeframe trend, and news evidence, and ranks the U.S. equity
universe by behavioral opportunity quality — never emitting a
buy/sell/long/short signal.

## Read this first: what's verified vs. what isn't

This sandbox has **no network access and no vendor API keys or live
database**. That constrains what could actually be executed here, and
I want that boundary to be explicit rather than blurred:

**Genuinely verified by running it (48 unit/performance tests, all
passing, zero third-party dependencies required):**
- The entire scoring stack: Behavior Score (7-factor), Structure,
  Liquidity, Historical (sample-gated), Multi-Timeframe Trend, News,
  Capital Efficiency, Confidence, and the Opportunity Score combiner
- The Multi-Timeframe Engine's alignment/persistence/acceleration/
  exhaustion math against synthetic bar series
- The full async ranking pipeline end-to-end against mock providers
  (`examples/run_demo.py` — actually run it, it works)
- Every real provider's **parsing logic** (Polygon snapshot/news,
  Finnhub earnings/insider/analyst, SEC EDGAR filings) against
  realistic mock JSON shaped like each vendor's documented response
- The universe filter and every safeguard (no-directional-language,
  no-unexplained-score)
- The insider-transaction neutral-language translation, proven not to
  leak "buy"/"sell" into output even though SEC Form 4 data genuinely
  uses those words
- **Load/performance behavior** (`tests/performance/test_load.py`): a
  200-symbol synthetic universe ranks in ~0.25s in this sandbox with no
  errors, 5 concurrent ranking runs don't corrupt each other's results,
  and a coarse linear-scaling check catches accidental O(n²) regressions

Run it yourself:
```bash
PYTHONPATH=. python3 -m unittest discover -s tests/unit -v         # 44 tests, no deps needed
PYTHONPATH=. python3 -m unittest discover -s tests/performance -v  # 4 more, no deps needed
PYTHONPATH=. python3 examples/run_demo.py                          # full pipeline, live output
```

**Written as real code, but NOT executed here (no network/keys/DB):**
- The actual HTTP-fetching methods on `PolygonMarketDataProvider`,
  `PolygonNewsProvider`, `FinnhubCorporateEventsProvider`,
  `SecEdgarFilingsMixin` — the endpoint paths and auth are written from
  my knowledge of each vendor's public docs, but I could not confirm
  today's exact response shape against a live call. Review against
  current vendor docs before depending on this in production.
- The WebSocket streaming client (`stream_quotes`) — needs the
  `websockets` package and a live connection to exercise the
  reconnect/backoff logic for real.
- Every database-touching test and route (`tests/api/`,
  `tests/providers/test_http_client.py`) — these need
  fastapi/httpx/sqlalchemy/aiosqlite installed, which this sandbox
  can't do. They're wired up to run in CI (`.github/workflows/ci.yml`)
  where dependencies actually get installed.
- `alembic/versions/0001_initial_schema.py` — hand-written to match
  `app/models/db_models.py` since there's no live DB here to
  autogenerate against. Run `alembic revision --autogenerate` against
  a real Postgres instance to check for drift before trusting it.

## What's genuinely new in this rewrite vs. the earlier `bpm-screener` prototype

- **Async throughout** — every provider interface and engine call is
  `async`, ready for real concurrent I/O against live vendors.
- **Real vendor clients, not just mocks** — Polygon.io (market data +
  news), Finnhub (earnings/insider/analyst), SEC EDGAR (free filings),
  each with retry/backoff/rate-limiting/caching via a shared
  `ResilientHttpClient`.
- **Multi-Timeframe Engine** — genuinely new: alignment, persistence,
  acceleration, exhaustion, and behavioral agreement across
  Daily/4H/1H/15m/5m/1m bar series, degrading gracefully (not
  fabricating) when some timeframes are unavailable.
- **Confidence Score and Capital Efficiency Score** as independent,
  fully-explained scores (not blended into the Opportunity Score).
- **A background scheduler** that continuously refreshes the universe
  and re-ranks it, persisting every run for `/history`.
- **A dashboard API** with 9 routes matching the brief exactly.

## Project layout

```
app/
  config.py, database.py, security.py, logging_config.py, main.py, scheduler.py, ranking_cache.py
  models/
    evidence.py, snapshot.py, ranking.py       Dataclass domain models
    db_models.py                                 Async SQLAlchemy schema (telemetry + Behavioral Database + rankings + audit)
    telemetry_schemas.py, api_schemas.py          Pydantic request/response schemas
  providers/
    base.py                                       6 abstract interfaces
    parsers.py                                    Pure parsing functions (zero third-party deps — see tests/unit/test_provider_parsers.py)
    http_client.py                                Shared rate-limit/retry/cache HTTP client
    polygon_market_data.py, polygon_news.py        Real Polygon.io clients
    finnhub_corporate_events.py                    Real Finnhub client
    sec_edgar_filings.py                           Real SEC EDGAR client (free)
    sentiment_provider.py                          Rule-based sentiment classifier
    db_historical_stats.py, db_behavioral_data.py  Database-backed providers
    factory.py                                     Mock/real provider switch
    mock/mock_providers.py                         Full async mock implementations
  engines/
    weights.py, universe.py, behavioral.py, structure.py, liquidity.py,
    historical.py, multi_timeframe.py, news_score.py, capital_efficiency.py,
    confidence.py, scoring.py, ranking.py
  research.py, safeguards.py
  routes/
    health.py, telemetry.py, scanner.py, rankings.py, news.py, behavior.py,
    history.py, statistics.py, research.py
alembic/                  Migration scaffolding (hand-written initial revision)
tests/
  unit/                    44 tests, zero dependencies, all passing — run these anywhere
  providers/               HTTP client tests (need httpx — CI only)
  api/                     Full API tests (need the full stack — CI only)
examples/run_demo.py       Actually-runnable end-to-end demo on mock data
```

## Non-negotiable rules enforced in code

- **Never BUY/SELL/LONG/SHORT** — `app/safeguards.py` scans every
  output-facing string before `build_ranking()` returns it, and
  `RankedSymbol` has no field for a directional instruction. Proven
  against a real edge case: SEC Form 4 filings literally categorize
  insider transactions as "Buy"/"Sell" — `describe_insider_transaction()`
  translates those to neutral language before they can reach output,
  and a full-pipeline test (`test_no_insider_transaction_language_leaks`)
  proves it holds end-to-end, not just in isolation.
- **No unexplained score** — `ScoreExplanation` refuses to construct
  without contributing factors and a methodology string.
- **No probability below sample size** — `score_historical()` zeroes
  value and confidence entirely below `HISTORICAL_MIN_SAMPLE_SIZE`.
- **Pine stays the source of truth for behavior** — nothing here
  recomputes BO/MC/state; `BehavioralDataProvider` only ever reads
  Pine's own confirmed telemetry.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit BPM_WEBHOOK_SECRET at minimum

# Option A: SQLite, no Docker
uvicorn app.main:app --reload

# Option B: Postgres via Docker Compose
docker compose up --build
```

Dev/test environments auto-create tables on startup; production does
not — run `alembic upgrade head` (preferred) or `scripts/create_tables.py`
(fallback) explicitly.

## Switching from mock to real providers

Nothing in `app/engines` changes. Flip the relevant `*_PROVIDER` env
var and supply the matching API key:

| Provider setting | Values | Needs |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `mock` \| `polygon` | `POLYGON_API_KEY` |
| `NEWS_PROVIDER` | `mock` \| `polygon` | `POLYGON_API_KEY` |
| `CORPORATE_EVENTS_PROVIDER` | `mock` \| `finnhub` | `FINNHUB_API_KEY` |
| `SENTIMENT_PROVIDER` | `mock` \| `rule_based` | (none — heuristic, not a vendor) |

`render.yaml` defaults every provider to `mock` even in production —
deliberately, so a fresh deploy never silently tries to call a vendor
with no key. Flip them once keys are set in the Render dashboard.

## Deploying

1. Push to GitHub — `.github/workflows/ci.yml` runs the full test suite
   (unit + provider + API) on every push/PR.
2. In Render, create a Blueprint from this repo — `render.yaml` defines
   the web service and a managed Postgres database.
3. Set `BPM_WEBHOOK_SECRET`, and `POLYGON_API_KEY`/`FINNHUB_API_KEY` if
   using real providers, in the Render dashboard (all marked
   `sync: false`, never committed).
4. Run `alembic upgrade head` against the Render Postgres instance once
   (production doesn't auto-create tables on startup).
5. Point the TradingView alert webhook at
   `https://<your-service>.onrender.com/webhook/telemetry`.

With `autoDeploy: true`, pushing to the connected branch redeploys
automatically.

## API endpoints

`/health`, `POST /webhook/telemetry`, `/scanner/top`,
`/scanner/ticker/{symbol}`, `/news/{symbol}`, `/behavior/{symbol}`,
`/rankings`, `/history`, `/history/{symbol}/full`, `/statistics`,
`/research`, `/research/{metric_name}`, `/openapi.json` (automatic via
FastAPI), `/docs` (automatic Swagger UI).

## Known limitations worth knowing about

- ~~The background scheduler runs as an asyncio task inside the web
  process~~ — **fixed**: `app/scheduler.py` now uses a Postgres session-held
  `pg_try_advisory_lock` for leader election, so a multi-instance Render
  deployment only runs one ranking loop at a time; a dead leader's lock
  releases automatically when its connection closes, and standby
  instances retry acquisition every `SCHEDULER_LEADER_RETRY_SECONDS`.
  Written for real, but not tested against a live Postgres in this
  sandbox — verify the advisory-lock behavior against your actual
  asyncpg setup before relying on it under real multi-instance load.
- ~~No load/performance tests~~ — **added**: `tests/performance/test_load.py`
  genuinely runs here (zero dependencies) and covers a 200-symbol
  universe, concurrent overlapping ranking runs, and a coarse
  linear-vs-quadratic scaling check. It measures the pure compute path
  against mock data — a real deployment's latency will be dominated by
  actual vendor API calls, which this can't measure without live
  network access.
- `Trend Score`'s confidence is capped low when multi-timeframe bar
  data isn't available, by design — it degrades rather than fabricates.
- `Forecast Reliability` is intentionally suppressed until the
  Behavioral Database has enough tracked occurrences to calibrate
  against — this mirrors Pine's own rule that a forecast bias is a
  diagnostic label, not a calibrated probability, until proven otherwise.
- Level II and options flow have no provider interface yet — out of
  scope until there's a concrete vendor to implement against.
