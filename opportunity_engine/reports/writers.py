"""Report writers.

Render a :class:`ScanResult` into the daily Markdown watchlist, CSV/JSON
exports, and themed sub-reports (top opportunities, sector, catalyst, IPO,
earnings). Every report carries the research-only disclaimer.

Research only. Not financial advice.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from pathlib import Path

from ..engine.opportunity_report import format_opportunity_md
from ..engine.pipeline import ScanResult
from ..models import DISCLAIMER, Opportunity

# Flat columns for the CSV export (mirrors the output spec).
CSV_COLUMNS = [
    "rank", "ticker", "company", "sector", "current_price",
    "aggressive_entry", "base_entry", "conservative_entry", "stop_loss",
    "target_1", "target_2", "target_3",
    "analyst_low", "analyst_mean", "analyst_high", "analyst_count",
    "expected_upside_pct", "risk_reward_ratio", "risk_level", "holding_period",
    "catalyst_timing", "catalyst_confidence",
    "technical_score", "fundamental_score", "quality_score", "catalyst_score",
    "earnings_score", "ipo_score", "analyst_score", "risk_score", "final_score",
    "top_catalyst", "tags",
    "data_flags", "fallback_used", "price_source", "analyst_targets_source",
    "catalyst_source",
]


def _row(opp: Opportunity) -> dict:
    p, s, a = opp.plan, opp.scores, opp.analyst
    top_cat = opp.catalyst.catalysts[0].description if opp.catalyst.catalysts else ""
    return {
        "rank": opp.rank, "ticker": opp.ticker, "company": opp.company,
        "sector": opp.sector, "current_price": opp.current_price,
        "aggressive_entry": p.aggressive_entry, "base_entry": p.base_entry,
        "conservative_entry": p.conservative_entry, "stop_loss": p.stop_loss,
        "target_1": p.target_1, "target_2": p.target_2, "target_3": p.target_3,
        "analyst_low": a.target_low, "analyst_mean": a.target_mean,
        "analyst_high": a.target_high, "analyst_count": a.num_analysts,
        "expected_upside_pct": round(opp.expected_upside_pct, 1),
        "risk_reward_ratio": p.risk_reward_ratio, "risk_level": opp.risk.level.value,
        "holding_period": p.holding_period,
        "catalyst_timing": opp.catalyst.catalyst_timing,
        "catalyst_confidence": opp.catalyst.catalyst_confidence,
        "technical_score": s.technical_score, "fundamental_score": s.fundamental_score,
        "quality_score": s.quality_score, "catalyst_score": s.catalyst_score,
        "earnings_score": s.earnings_score, "ipo_score": s.ipo_score,
        "analyst_score": s.analyst_score, "risk_score": s.risk_score,
        "final_score": s.final_score,
        "top_catalyst": top_cat, "tags": "; ".join(opp.tags),
        "data_flags": "; ".join(opp.provenance.flags),
        "fallback_used": opp.provenance.fallback_used,
        "price_source": opp.provenance.price_source,
        "analyst_targets_source": opp.provenance.analyst_targets_source,
        "catalyst_source": opp.provenance.catalyst_source,
    }


# --------------------------------------------------------------------------- #
# Renderers (return strings)
# --------------------------------------------------------------------------- #
def _header(result: ScanResult, title: str) -> list[str]:
    return [
        f"# {title}",
        f"*As of {result.as_of.isoformat()} · provider: {result.provider} · "
        f"{len(result.opportunities)} candidates scanned*",
        "",
        f"> **{DISCLAIMER}**",
        "",
    ]


def _flag_summary(result: ScanResult) -> dict[str, int]:
    counts: dict[str, int] = {}
    for o in result.opportunities:
        for f in o.provenance.flags:
            counts[f] = counts.get(f, 0) + 1
    return counts


def render_daily_markdown(result: ScanResult) -> str:
    out = _header(result, "Daily Opportunity Watchlist")
    counts = _flag_summary(result)
    if counts:
        out.append("**Data quality:** " + " · ".join(
            f"{k}={v}" for k, v in sorted(counts.items())) )
        out.append("")
    top = result.top
    # Quick summary table.
    out.append("| # | Ticker | Score | Risk | Upside | R/R | Top Catalyst |")
    out.append("|--:|:------|------:|:-----|-------:|----:|:-------------|")
    for o in top:
        cat = o.catalyst.catalysts[0].description if o.catalyst.catalysts else "-"
        out.append(
            f"| {o.rank} | {o.ticker} | {o.scores.final_score:.0f} | {o.risk.level.value} | "
            f"{o.expected_upside_pct:.0f}% | {o.plan.risk_reward_ratio:.1f} | {cat} |"
        )
    out.append("")
    out.append("---")
    out.append("")
    for o in top:
        out.append(format_opportunity_md(o))
        out.append("")
    out.append(f"\n*{DISCLAIMER}*")
    return "\n".join(out)


def render_csv(result: ScanResult) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for o in result.opportunities:
        writer.writerow(_row(o))
    return buf.getvalue()


def render_json(result: ScanResult) -> str:
    payload = {
        "as_of": result.as_of.isoformat(),
        "provider": result.provider,
        "disclaimer": DISCLAIMER,
        "count": len(result.opportunities),
        "data_quality": _flag_summary(result),
        "opportunities": [o.to_dict() for o in result.opportunities],
    }
    return json.dumps(payload, indent=2)


def render_top_report(result: ScanResult, n: int = 5) -> str:
    out = _header(result, f"Top {n} Opportunities")
    for o in result.opportunities[:n]:
        out.append(format_opportunity_md(o))
        out.append("")
    out.append(f"*{DISCLAIMER}*")
    return "\n".join(out)


def render_sector_report(result: ScanResult) -> str:
    out = _header(result, "Sector Report")
    by_sector: dict[str, list[Opportunity]] = defaultdict(list)
    for o in result.opportunities:
        by_sector[o.sector].append(o)
    rows = []
    for sector, opps in by_sector.items():
        avg = sum(o.scores.final_score for o in opps) / len(opps)
        rows.append((avg, sector, opps))
    rows.sort(reverse=True)
    out.append("| Sector | Names | Avg Score | Leaders |")
    out.append("|:-------|------:|----------:|:--------|")
    for avg, sector, opps in rows:
        leaders = ", ".join(o.ticker for o in sorted(opps, key=lambda x: -x.scores.final_score)[:3])
        out.append(f"| {sector} | {len(opps)} | {avg:.0f} | {leaders} |")
    out.append("")
    out.append(f"*{DISCLAIMER}*")
    return "\n".join(out)


def render_catalyst_report(result: ScanResult) -> str:
    out = _header(result, "Catalyst Report")
    ranked = sorted(result.opportunities, key=lambda o: -o.scores.catalyst_score)
    out.append("| Ticker | Catalyst Score | Confidence | Timing | Primary Catalyst |")
    out.append("|:-------|---------------:|:-----------|:-------|:-----------------|")
    for o in ranked[: result.settings.top_n]:
        c = o.catalyst
        primary = c.catalysts[0].description if c.catalysts else "-"
        out.append(
            f"| {o.ticker} | {c.catalyst_score:.0f} | {c.catalyst_confidence:.0%} | "
            f"{c.catalyst_timing} | {primary} |"
        )
    out.append("")
    out.append(f"*{DISCLAIMER}*")
    return "\n".join(out)


def render_ipo_report(result: ScanResult) -> str:
    out = _header(result, "IPO Report")
    ipos = [o for o in result.opportunities if o.ipo.is_recent or o.ipo.is_upcoming]
    if not ipos:
        out.append("_No recent or upcoming IPOs in the current universe._")
        out.append("")
        out.append(f"*{DISCLAIMER}*")
        return "\n".join(out)
    out.append("| Ticker | Status | IPO Price | 30d | 90d | 180d | Rev Growth | Score |")
    out.append("|:-------|:-------|----------:|----:|----:|-----:|-----------:|------:|")
    for o in sorted(ipos, key=lambda x: -x.scores.ipo_score):
        i = o.ipo
        status = "Upcoming" if i.is_upcoming else "Recent"
        out.append(
            f"| {o.ticker} | {status} | "
            f"{('$%.2f' % i.ipo_price) if i.ipo_price else '-'} | "
            f"{('%.0f%%' % i.perf_30d) if i.perf_30d is not None else '-'} | "
            f"{('%.0f%%' % i.perf_90d) if i.perf_90d is not None else '-'} | "
            f"{('%.0f%%' % i.perf_180d) if i.perf_180d is not None else '-'} | "
            f"{('%.0f%%' % i.revenue_growth) if i.revenue_growth is not None else '-'} | "
            f"{o.scores.ipo_score:.0f} |"
        )
    out.append("")
    out.append(f"*{DISCLAIMER}*")
    return "\n".join(out)


def render_earnings_report(result: ScanResult) -> str:
    out = _header(result, "Earnings Report")
    dated = [o for o in result.opportunities if o.earnings.days_until_earnings is not None]
    dated.sort(key=lambda o: o.earnings.days_until_earnings or 999)
    out.append("| Ticker | Next Earnings | Days | Guidance Rev | Earnings Score |")
    out.append("|:-------|:--------------|-----:|-------------:|---------------:|")
    for o in dated[: result.settings.top_n]:
        e = o.earnings
        nd = e.next_earnings_date.isoformat() if e.next_earnings_date else "-"
        gr = f"{e.guidance_revision:+.1f}%" if e.guidance_revision is not None else "-"
        out.append(
            f"| {o.ticker} | {nd} | {e.days_until_earnings} | {gr} | "
            f"{o.scores.earnings_score:.0f} |"
        )
    out.append("")
    out.append(f"*{DISCLAIMER}*")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Disk writer
# --------------------------------------------------------------------------- #
def write_all_reports(result: ScanResult, output_dir: str | None = None) -> dict[str, str]:
    out_dir = Path(output_dir or result.settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = result.as_of.isoformat()

    files = {
        f"watchlist_{stamp}.md": render_daily_markdown(result),
        f"watchlist_{stamp}.csv": render_csv(result),
        f"watchlist_{stamp}.json": render_json(result),
        f"top5_{stamp}.md": render_top_report(result, 5),
        f"sector_{stamp}.md": render_sector_report(result),
        f"catalyst_{stamp}.md": render_catalyst_report(result),
        f"ipo_{stamp}.md": render_ipo_report(result),
        f"earnings_{stamp}.md": render_earnings_report(result),
    }
    written: dict[str, str] = {}
    for name, content in files.items():
        path = out_dir / name
        path.write_text(content)
        written[name] = str(path)
    return written
