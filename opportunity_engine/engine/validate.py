"""Data validation.

Powers ``python -m opportunity_engine validate``. For each requested ticker it
fetches every field group through the provider stack (with provenance), then
reports the data source used per field, which fields are missing or fell back to
the mock, any staleness warnings, and an overall *candidate readiness score*.

Readiness blends completeness (is the field populated at all) with liveness (did
it come from the live provider) and applies a staleness penalty, so a fully-live
fresh name scores ~100 while an all-mock candidate scores ~60 (complete but
synthetic).

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..config import Settings
from ..data_ingest import build_provider
from ..models import DISCLAIMER, DataFlag
from .pipeline import FetchedData, _primary_name, fetch_all

# (group, completeness predicate, weight)
_GROUPS = [
    ("price", lambda d: bool(d.history and len(d.history) >= 30), 0.30),
    ("analyst", lambda d: bool(d.analyst.num_analysts or d.analyst.target_mean), 0.25),
    ("catalyst", lambda d: len(d.catalyst.catalysts) >= 1, 0.15),
    ("fundamentals", lambda d: d.fundamentals.revenue_growth is not None
        or d.fundamentals.gross_margin is not None, 0.15),
    ("earnings", lambda d: d.earnings.next_earnings_date is not None
        or bool(d.earnings.surprises), 0.10),
    ("ipo", lambda d: d.ipo is not None, 0.05),
]

_SOURCE_ATTR = {
    "price": "price_source",
    "analyst": "analyst_targets_source",
    "catalyst": "catalyst_source",
    "fundamentals": "fundamentals_source",
    "earnings": "earnings_source",
    "ipo": "ipo_source",
}


@dataclass
class ValidationReport:
    ticker: str
    ok: bool
    sources: dict[str, str] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    fallback_fields: list[str] = field(default_factory=list)
    stale_warnings: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    readiness: float = 0.0


def validate_ticker(provider, ticker: str, settings: Settings,
                    today: date | None = None) -> ValidationReport:
    data: FetchedData | None = fetch_all(provider, ticker, settings, today=today)
    if data is None:
        return ValidationReport(
            ticker=ticker, ok=False,
            missing_fields=["price (no usable history — candidate cannot be built)"],
            flags=[DataFlag.MOCK_DATA.value], readiness=0.0,
        )

    prov = data.provenance
    primary = _primary_name(provider)

    sources = {g: getattr(prov, _SOURCE_ATTR[g]) for g, _, _ in _GROUPS}

    completeness = 0.0
    liveness = 0.0
    for group, present, weight in _GROUPS:
        if present(data):
            completeness += weight
        if primary is not None and sources[group] == primary:
            liveness += weight

    stale_penalty = 15.0 if DataFlag.STALE_DATA.value in prov.flags else 0.0
    readiness = max(0.0, (0.6 * completeness + 0.4 * liveness) * 100.0 - stale_penalty)

    return ValidationReport(
        ticker=ticker, ok=True, sources=sources,
        missing_fields=list(prov.missing_fields),
        fallback_fields=list(prov.fallback_fields),
        stale_warnings=list(prov.stale_warnings),
        flags=list(prov.flags),
        readiness=round(readiness, 1),
    )


def run_validation(tickers: list[str], settings: Settings) -> list[ValidationReport]:
    provider = build_provider(settings)
    return [validate_ticker(provider, t.strip().upper(), settings) for t in tickers if t.strip()]


def render_validation(tickers: list[str], settings: Settings) -> str:
    provider = build_provider(settings)
    reports = [validate_ticker(provider, t.strip().upper(), settings)
               for t in tickers if t.strip()]
    out = [
        f"# Data Validation — provider: {provider.name}",
        f"> {DISCLAIMER}",
        "",
    ]
    for r in reports:
        out.append(f"## {r.ticker}  —  readiness {r.readiness:.0f}/100  "
                   f"[{', '.join(r.flags) or 'MOCK_DATA'}]")
        if not r.ok:
            out.append("  ❌ No usable price history; candidate cannot be built.")
            out.append("")
            continue
        out.append("  Data sources:")
        for group, src in r.sources.items():
            tag = "live" if src not in ("mock",) else "mock"
            out.append(f"    - {group:<13} {src:<14} ({tag})")
        out.append(f"  Fallback fields : {', '.join(r.fallback_fields) or 'none'}")
        out.append(f"  Missing fields  : {', '.join(r.missing_fields) or 'none'}")
        out.append(f"  Stale warnings  : {'; '.join(r.stale_warnings) or 'none'}")
        out.append("")
    out.append(DISCLAIMER)
    return "\n".join(out)
