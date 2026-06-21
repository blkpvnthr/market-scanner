"""Risk engine.

Produces a structured ``RiskAssessment`` (per-factor Low/Medium/High labels and
an overall level) plus a 0..100 ``risk_score`` where *higher means safer* so it
can be blended directly into the final score.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    FundamentalFeatures,
    IPOFeatures,
    RiskAssessment,
    RiskLevel,
    TechnicalFeatures,
)
from ._util import clamp


@dataclass
class RiskResult:
    assessment: RiskAssessment
    risk_score: float  # 0..100, higher = safer


def _label(value: float) -> str:
    if value < 33:
        return "Low"
    if value < 66:
        return "Medium"
    return "High"


# Sectors carrying elevated geopolitical / regulatory exposure in the model.
_GEO_SECTORS = {"Semiconductors", "Defense", "Quantum"}
_REG_SECTORS = {"Biotech", "Defense", "Energy"}


def assess_risk(
    fundamentals: FundamentalFeatures,
    technicals: TechnicalFeatures,
    ipo: IPOFeatures,
    sector: str,
) -> RiskResult:
    factors: dict[str, str] = {}
    notes: list[str] = []
    penalties: list[float] = []  # 0..100 each, higher = riskier

    # Valuation risk — rich multiples.
    val_risk = clamp(((fundamentals.pe or 25) - 20) * 1.4 + ((fundamentals.ps or 5) - 5) * 2)
    factors["valuation"] = _label(val_risk)
    penalties.append(val_risk)
    if val_risk > 66:
        notes.append("Premium valuation leaves little margin for error.")

    # Earnings risk — negative drift / weak guidance.
    earn_risk = 50.0
    if fundamentals.eps_growth is not None and fundamentals.eps_growth < 0:
        earn_risk = 70.0
    factors["earnings"] = _label(earn_risk)
    penalties.append(earn_risk)

    # Debt risk — from cash/debt ratio.
    cd = fundamentals.cash_debt_ratio
    debt_risk = clamp(80 - (cd or 1.0) * 25)
    factors["debt"] = _label(debt_risk)
    penalties.append(debt_risk)
    if debt_risk > 66:
        notes.append("Leverage is elevated relative to cash on hand.")

    # Dilution risk — pre-revenue / IPO / high-vol names dilute more.
    dilution = 35.0
    if ipo.is_recent or ipo.is_upcoming:
        dilution = 65.0
    if (fundamentals.operating_margin or 0) < 0:
        dilution += 15
    dilution = clamp(dilution)
    factors["dilution"] = _label(dilution)
    penalties.append(dilution)

    # Customer concentration — heuristic by sector.
    conc = 60.0 if sector in {"Semiconductors", "Aerospace", "Defense"} else 35.0
    factors["customer_concentration"] = _label(conc)
    penalties.append(conc)

    # Competition.
    comp = 60.0 if sector in {"Technology", "Semiconductors", "Autos"} else 45.0
    factors["competition"] = _label(comp)
    penalties.append(comp)

    # Geopolitical & regulatory.
    geo = 70.0 if sector in _GEO_SECTORS else 35.0
    factors["geopolitical"] = _label(geo)
    penalties.append(geo)
    if geo > 66:
        notes.append("Exposed to export controls / geopolitical supply-chain risk.")

    reg = 70.0 if sector in _REG_SECTORS else 35.0
    factors["regulatory"] = _label(reg)
    penalties.append(reg)

    # Liquidity & volatility — from technical volatility score.
    liq = clamp(technicals.volatility_score)
    factors["liquidity"] = _label(liq)
    penalties.append(liq)

    avg_penalty = sum(penalties) / len(penalties)
    risk_score = round(clamp(100 - avg_penalty), 1)  # higher = safer

    # Overall level.
    if ipo.is_upcoming or (ipo.is_recent and technicals.volatility_score > 60):
        level = RiskLevel.SPECULATIVE
    elif avg_penalty < 40:
        level = RiskLevel.LOW
    elif avg_penalty < 58:
        level = RiskLevel.MEDIUM
    elif avg_penalty < 72:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.SPECULATIVE

    return RiskResult(
        assessment=RiskAssessment(level=level, factors=factors, notes=notes),
        risk_score=risk_score,
    )
