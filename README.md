# Opportunity Engine

A **research-first** investment opportunity scanner. It discovers, scores, ranks
and **explains** investment opportunities across growth, value, quality
compounders, recent/upcoming IPOs, earnings setups, and news/catalyst-driven
ideas — and emits a ranked daily watchlist with entry/exit plans, analyst
expectations, catalyst analysis and risk assessments.

> **Research only. Not financial advice.** This platform performs **no automated
> trading and no order execution**, and requires **no broker credentials**.

---

## Why it always runs

Every data provider degrades gracefully **per field**. With **no API keys at
all**, the engine runs end-to-end on a deterministic **mock provider** that
generates realistic OHLCV series (so technical indicators are genuine) plus
plausible fundamentals, earnings, IPO, analyst and catalyst data. Add keys later
to layer in real data — nothing else changes.

Every opportunity carries **provenance**: the source of each field
(`price_source`, `analyst_targets_source`, `catalyst_source`, …) and data-quality
flags — `LIVE_DATA`, `PARTIAL_LIVE_DATA`, `MOCK_DATA`, `STALE_DATA`,
`MISSING_ANALYST_TARGETS` — so you always know what's real. A single missing live
field falls back to the mock for that field only; it never silently replaces the
whole scan. Inspect it with `validate`:

```bash
python -m opportunity_engine validate --provider yahoo --tickers ASML,NVDA,RKLB
```

## Install

```bash
# Core needs only the standard library. Optional extras enable real providers:
pip install -e ".[providers,dashboard,dev]"
# or
pip install -r requirements.txt
```

## Quick start

```bash
python -m opportunity_engine scan            # ranked watchlist to stdout
python -m opportunity_engine scan --top 20   # show more names
python -m opportunity_engine detail          # full per-opportunity blocks
python -m opportunity_engine report          # write MD / CSV / JSON + sub-reports
python -m opportunity_engine portfolio       # model portfolios (Phase 4)
python -m opportunity_engine backfill        # snapshot scores to SQLite
python -m opportunity_engine dashboard       # Streamlit UI (needs streamlit)

# Data provenance / readiness for specific tickers:
python -m opportunity_engine validate --provider yahoo --tickers ASML,NVDA,RKLB

# Email the full report (>=20 candidates, ranked best->worst by max return):
python -m opportunity_engine email --dry-run --html-out preview.html   # preview
python -m opportunity_engine email                                     # send (needs SMTP)

# Use real data once keys are set (see below):
python -m opportunity_engine scan --provider yahoo
```

### Scheduled delivery (serverless, no laptop required)

Get the report emailed **every weekday at 08:30** via GitHub Actions (free) or
AWS Lambda — both DST-safe. See **[DEPLOY.md](DEPLOY.md)**. The emailed report is
always ≥ 20 candidates ranked best→worst by maximum modelled return (upside to
T3), with CSV + JSON attached.

## Configuration

Reads `./.env` (or the real environment). All keys are optional:

| Variable | Provider |
|---|---|
| `APCA_API_KEY`, `APCA_SECRET_KEY` | Alpaca (data only) |
| `FINNHUB_API_KEY` | Finnhub |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage |
| `OE_PROVIDER` | `mock` (default) · `yahoo` · `alpaca` · `finnhub` · `alpha_vantage` |
| `OE_WATCHLIST` | comma-separated tickers |
| `OE_TOP_N`, `OE_OUTPUT_DIR`, `OE_SEED` | scan tuning |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | email delivery (`email` command) |
| `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_TOP_N` | email recipients / size (≥ 20) |

See `.env.example` for a template.

When a selected provider lacks a key/library it transparently falls back to the
mock, so a scan never fails.

## Architecture

```
opportunity_engine/
  config.py              # typed Settings, .env loading, weights
  models.py              # dataclasses: the shared contract (+ JSON serialization)
  data_ingest/           # provider abstraction + graceful degradation
    base.py              #   DataProvider ABC + FallbackProvider
    mock_provider.py     #   deterministic synthetic data (Phase-1 default)
    yahoo_/alpaca_/finnhub_/alpha_vantage_provider.py
    market_data.py news.py fundamentals.py earnings.py ipo_calendar.py analyst_targets.py
  features/              # technicals + component scorers
    technicals.py catalyst_score.py fundamental_score.py earnings_score.py
    ipo_score.py risk_score.py analyst_score.py
  engine/
    universe.py          # daily candidate universe (themes + IPOs + watchlist)
    scorer.py            # transparent weighted final score (all sub-scores kept)
    entry_exit_engine.py # 3 entries, ATR/support stop, 3 layered targets, R/R
    thesis_generator.py  # bull / bear / base + key catalysts & risks
    ranker.py            # deterministic ranking
    opportunity_report.py# per-opportunity Markdown
    pipeline.py          # orchestrator -> ScanResult
    validate.py          # data-source / readiness validation
  reports/
    writers.py           # daily MD, CSV, JSON, sector/catalyst/IPO/earnings
    email.py             # HTML email (>=20 candidates by max return) + SMTP
  portfolio/constructor.py # Phase-4 model portfolios + risk/Sharpe estimates
  storage/cache.py       # TTL cache + SQLite history snapshots
  dash/streamlit_app.py  # Phase-3 dashboard
  serverless.py          # AWS Lambda / cron entrypoint (run scan + email)
.github/workflows/daily-report.yml  # weekday 08:30 serverless schedule
tests/                   # full unit-test suite (stdlib-only, no network)
```

## Scoring (transparent, 0–100)

The final score is a weighted blend of component scores, **all of which are
returned** on each opportunity:

`technical · fundamental · quality · catalyst · earnings · ipo · analyst · risk`

The IPO component only participates for genuine recent/upcoming IPOs; otherwise
its weight is redistributed so seasoned names aren't penalised. Weights are
configurable in `config.DEFAULT_WEIGHTS`.

Every opportunity is guaranteed to carry **at least one catalyst** and a full
generated thesis (summary + bull/bear/base + key catalysts + key risks).

## Output

`scan`/`report` produce, per opportunity: ticker, company, current price, three
entry zones, stop, three targets, analyst low/mean/high + count, expected upside,
risk/reward, risk level, holding period, catalysts (+ confidence & timing),
thesis, bull/bear/base cases, key risks and the full score breakdown — plus the
research-only disclaimer.

## Testing

```bash
pytest          # 28 tests, no network or API keys required
```

## Roadmap

- **Phase 1 (done):** structure, config, mock provider, technical scanner,
  scoring, entry/exit, thesis, MD/CSV/JSON reports, unit tests.
- **Phase 2:** real providers (Alpaca, Finnhub, Yahoo, Alpha Vantage), news
  sentiment, fundamentals, earnings, IPO calendars, caching. *(provider
  scaffolding + caching in place.)*
- **Phase 3:** Streamlit dashboard *(in place)*, historical performance,
  score backtesting, sector rotation, analyst-revision tracking, alerting,
  email/Discord reports.
- **Phase 4:** portfolio construction *(in place)* — Top 5/10, concentrated,
  growth, quality, with sizing, sector caps and return/vol/drawdown/Sharpe.

---

**Research only. Not financial advice.** No automated buying or selling.
