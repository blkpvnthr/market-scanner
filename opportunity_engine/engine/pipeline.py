"""Scan pipeline — the orchestrator.

For each universe entry it: pulls provider data, computes technicals and every
component score, builds the entry/exit plan, assesses risk, generates the thesis,
and assembles an :class:`Opportunity`. The list is then ranked. This is the
single entry point used by the CLI, the reports and the dashboard.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..config import Settings, load_settings
from ..data_ingest import DataProvider, build_provider
from ..data_ingest.base import FetchResult, fetch_sourced
from ..features import compute_technicals
from ..models import (
    AnalystTargets,
    CatalystFeatures,
    DataFlag,
    DataProvenance,
    EarningsFeatures,
    FundamentalFeatures,
    IPOFeatures,
    Opportunity,
    PriceHistory,
    TechnicalFeatures,
)
from .entry_exit_engine import build_plan
from .ranker import rank_opportunities
from .scorer import compute_scores
from .thesis_generator import generate_thesis
from .universe import UniverseEntry, build_universe

# A live daily bar older than this many calendar days is considered stale.
STALE_WINDOW_DAYS = 6
# Minimum bars required to compute a meaningful candidate.
MIN_BARS = 30


@dataclass
class ScanResult:
    as_of: date
    provider: str
    opportunities: list[Opportunity]      # full ranked list
    settings: Settings

    @property
    def top(self) -> list[Opportunity]:
        return self.opportunities[: self.settings.top_n]


@dataclass
class FetchedData:
    """Raw provider data for one ticker plus its provenance."""
    ticker: str
    history: PriceHistory
    company: str
    sector: str
    fundamentals: FundamentalFeatures
    earnings: EarningsFeatures
    ipo: IPOFeatures
    analyst: AnalystTargets
    catalyst: CatalystFeatures
    provenance: DataProvenance


def _primary_name(provider: DataProvider) -> str | None:
    """Name of the live primary, or None for a mock-only provider."""
    primary = getattr(provider, "primary", None)
    return getattr(primary, "name", None) if primary is not None else None


def fetch_all(provider: DataProvider, ticker: str, settings: Settings,
              today: date | None = None) -> FetchedData | None:
    """Fetch every field group for ``ticker`` with full source tracking.

    Returns ``None`` when no usable price history can be obtained (the one field
    a candidate cannot do without). All other fields fall back to the mock
    individually, so a single missing live field never sinks the whole candidate.
    """
    today = today or date.today()
    primary_name = _primary_name(provider)

    results: dict[str, FetchResult] = {
        "price": fetch_sourced(provider, "get_price_history", ticker, settings.history_days),
        "company": fetch_sourced(provider, "get_company_name", ticker),
        "sector": fetch_sourced(provider, "get_sector", ticker),
        "fundamentals": fetch_sourced(provider, "get_fundamentals", ticker),
        "earnings": fetch_sourced(provider, "get_earnings", ticker),
        "ipo": fetch_sourced(provider, "get_ipo", ticker),
        "analyst": fetch_sourced(provider, "get_analyst_targets", ticker),
        "catalyst": fetch_sourced(provider, "get_catalysts", ticker),
    }

    history = results["price"].value
    if not history or len(history) < MIN_BARS:
        return None

    company = results["company"].value or f"{ticker} Inc."
    sector = results["sector"].value or "Diversified"
    fundamentals = results["fundamentals"].value or FundamentalFeatures()
    earnings = results["earnings"].value or EarningsFeatures()
    ipo = results["ipo"].value or IPOFeatures()
    analyst = results["analyst"].value or AnalystTargets()
    catalyst = results["catalyst"].value or CatalystFeatures()

    prov = DataProvenance(
        price_source=results["price"].source,
        company_source=results["company"].source,
        sector_source=results["sector"].source,
        fundamentals_source=results["fundamentals"].source,
        earnings_source=results["earnings"].source,
        ipo_source=results["ipo"].source,
        analyst_targets_source=results["analyst"].source,
        catalyst_source=results["catalyst"].source,
        last_price_date=history.bars[-1].dt if history.bars else None,
    )
    prov.fallback_fields = [name for name, r in results.items() if r.fallback_used]
    prov.fallback_used = bool(prov.fallback_fields)
    prov.missing_fields = [name for name, r in results.items() if not r.value]

    # --- flags --------------------------------------------------------------
    if primary_name is None:
        prov.flags = [DataFlag.MOCK_DATA.value]
    else:
        live_fields = [n for n, r in results.items()
                       if not r.fallback_used and r.source == primary_name]
        if not live_fields:
            prov.flags = [DataFlag.MOCK_DATA.value]
        elif not prov.fallback_fields:
            prov.flags = [DataFlag.LIVE_DATA.value]
        else:
            prov.flags = [DataFlag.PARTIAL_LIVE_DATA.value]

        # Staleness only applies to genuinely live price data.
        if prov.price_source == primary_name and prov.last_price_date:
            age = (today - prov.last_price_date).days
            if age > STALE_WINDOW_DAYS:
                prov.flags.append(DataFlag.STALE_DATA.value)
                prov.stale_warnings.append(
                    f"Latest live price bar is {age}d old ({prov.last_price_date.isoformat()})."
                )

        # Analyst coverage absent from the live source.
        if prov.analyst_targets_source != primary_name or analyst.num_analysts == 0:
            prov.flags.append(DataFlag.MISSING_ANALYST_TARGETS.value)

    return FetchedData(
        ticker=ticker, history=history, company=company, sector=sector,
        fundamentals=fundamentals, earnings=earnings, ipo=ipo,
        analyst=analyst, catalyst=catalyst, provenance=prov,
    )


def evaluate_ticker(
    provider: DataProvider, entry: UniverseEntry, settings: Settings, as_of: date
) -> Opportunity | None:
    ticker = entry.ticker
    data = fetch_all(provider, ticker, settings)
    if data is None:
        return None

    history = data.history
    current_price = history.last_close
    company, sector = data.company, data.sector
    fundamentals, earnings = data.fundamentals, data.earnings
    ipo, analyst, catalyst = data.ipo, data.analyst, data.catalyst

    technicals: TechnicalFeatures = compute_technicals(history)

    scoring = compute_scores(
        technicals=technicals,
        fundamentals=fundamentals,
        earnings=earnings,
        ipo=ipo,
        analyst=analyst,
        catalyst=catalyst,
        sector=sector,
        current_price=current_price,
        weights=settings.weights,
    )

    plan = build_plan(current_price, technicals, analyst)

    thesis = generate_thesis(
        ticker=ticker,
        company=company,
        sector=sector,
        fundamentals=fundamentals,
        catalyst=catalyst,
        analyst=analyst,
        scores=scoring.scores,
        risk=scoring.risk,
        plan=plan,
    )

    return Opportunity(
        ticker=ticker,
        company=company,
        sector=sector,
        as_of=as_of,
        current_price=round(current_price, 2),
        tags=entry.tag_labels,
        technicals=technicals,
        fundamentals=fundamentals,
        earnings=earnings,
        ipo=ipo,
        analyst=analyst,
        catalyst=catalyst,
        scores=scoring.scores,
        plan=plan,
        risk=scoring.risk,
        thesis=thesis,
        provenance=data.provenance,
    )


def run_scan(settings: Settings | None = None, as_of: date | None = None) -> ScanResult:
    settings = settings or load_settings()
    as_of = as_of or date(2026, 6, 19)
    provider = build_provider(settings)

    universe = build_universe(settings)
    opportunities: list[Opportunity] = []
    for entry in universe:
        try:
            opp = evaluate_ticker(provider, entry, settings, as_of)
        except Exception:
            opp = None
        if opp is not None:
            opportunities.append(opp)

    ranked = rank_opportunities(opportunities)
    return ScanResult(
        as_of=as_of,
        provider=provider.name,
        opportunities=ranked,
        settings=settings,
    )
