"""Portfolio construction engine (Phase 4).

Turns a ranked opportunity list into several model portfolios with score-based
position sizing, a sector-concentration cap, and estimated return / volatility /
drawdown / Sharpe. This is a *research* sizing aid only — it places no orders.

Research only. Not financial advice.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ..models import DISCLAIMER, Opportunity

RISK_FREE = 4.0          # % annual, for Sharpe
SECTOR_CAP = 0.40        # max aggregate weight per sector


@dataclass
class PortfolioPosition:
    ticker: str
    sector: str
    weight: float                # 0..1
    final_score: float
    expected_upside_pct: float
    risk_level: str


@dataclass
class Portfolio:
    name: str
    positions: list[PortfolioPosition] = field(default_factory=list)
    expected_return_pct: float = 0.0
    expected_volatility_pct: float = 0.0
    expected_drawdown_pct: float = 0.0
    sharpe: float = 0.0
    disclaimer: str = DISCLAIMER


def _annualized_vol(opp: Opportunity) -> float:
    # Map the 0..100 volatility score to a rough annualized vol (15%..70%).
    v = opp.technicals.volatility_score or 40.0
    return 15.0 + v / 100.0 * 55.0


def _size_positions(opps: list[Opportunity], concentrate: bool) -> list[PortfolioPosition]:
    if not opps:
        return []
    # Raw weights from score (optionally squared to concentrate in leaders).
    raw = {}
    for o in opps:
        base = max(o.scores.final_score, 1.0)
        raw[o.ticker] = base ** (2.0 if concentrate else 1.0)

    # Apply sector cap iteratively.
    sectors = {o.ticker: o.sector for o in opps}
    total = sum(raw.values())
    weights = {t: w / total for t, w in raw.items()}
    for _ in range(5):
        by_sector: dict[str, float] = defaultdict(float)
        for t, w in weights.items():
            by_sector[sectors[t]] += w
        over = {s: tot for s, tot in by_sector.items() if tot > SECTOR_CAP}
        if not over:
            break
        for s, tot in over.items():
            scale = SECTOR_CAP / tot
            for t in weights:
                if sectors[t] == s:
                    weights[t] *= scale
        tot_w = sum(weights.values())
        weights = {t: w / tot_w for t, w in weights.items()}

    out = []
    for o in sorted(opps, key=lambda x: -weights[x.ticker]):
        out.append(PortfolioPosition(
            ticker=o.ticker, sector=o.sector, weight=round(weights[o.ticker], 4),
            final_score=o.scores.final_score,
            expected_upside_pct=round(o.expected_upside_pct, 1),
            risk_level=o.risk.level.value,
        ))
    return out


def _build(name: str, opps: list[Opportunity], concentrate: bool = False) -> Portfolio:
    positions = _size_positions(opps, concentrate)
    wmap = {p.ticker: p.weight for p in positions}
    omap = {o.ticker: o for o in opps}

    exp_return = sum(p.weight * p.expected_upside_pct for p in positions)
    # Portfolio vol assuming average pairwise correlation of 0.4 (diversification).
    indiv_vol = {t: _annualized_vol(omap[t]) for t in wmap}
    var = 0.0
    rho = 0.4
    for ti, wi in wmap.items():
        for tj, wj in wmap.items():
            corr = 1.0 if ti == tj else rho
            var += wi * wj * indiv_vol[ti] * indiv_vol[tj] * corr
    vol = var ** 0.5
    drawdown = sum(p.weight * omap[p.ticker].plan.max_drawdown_estimate for p in positions)
    sharpe = round((exp_return - RISK_FREE) / vol, 2) if vol else 0.0

    return Portfolio(
        name=name,
        positions=positions,
        expected_return_pct=round(exp_return, 1),
        expected_volatility_pct=round(vol, 1),
        expected_drawdown_pct=round(drawdown, 1),
        sharpe=sharpe,
    )


def build_portfolios(opportunities: list[Opportunity]) -> dict[str, Portfolio]:
    """Construct the standard set of model portfolios from ranked opportunities."""
    ranked = sorted(opportunities, key=lambda o: -o.scores.final_score)
    growth = sorted(
        [o for o in ranked if (o.fundamentals.revenue_growth or 0) >= 20],
        key=lambda o: -(o.fundamentals.revenue_growth or 0),
    )[:10]
    quality = sorted(ranked, key=lambda o: -o.scores.quality_score)[:10]

    return {
        "top5": _build("Top 5", ranked[:5]),
        "top10": _build("Top 10", ranked[:10]),
        "concentrated": _build("Concentrated", ranked[:5], concentrate=True),
        "growth": _build("Growth", growth or ranked[:10]),
        "quality": _build("Quality", quality),
    }
