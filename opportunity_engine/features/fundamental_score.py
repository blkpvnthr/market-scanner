"""Fundamental scoring: fundamental, quality, valuation and financial-strength.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import FundamentalFeatures
from ._util import clamp, scale


@dataclass
class FundamentalScores:
    fundamental_score: float = 50.0
    quality_score: float = 50.0
    valuation_score: float = 50.0
    financial_strength_score: float = 50.0


def score_fundamentals(f: FundamentalFeatures) -> FundamentalScores:
    """Return the four fundamental sub-scores (each 0..100)."""
    # Growth component.
    growth = (scale(f.revenue_growth, 0, 60) * 0.6 + scale(f.eps_growth, -10, 80) * 0.4)

    # Quality: margins + returns on capital.
    quality = (
        scale(f.gross_margin, 20, 80) * 0.3
        + scale(f.operating_margin, 0, 45) * 0.25
        + scale(f.roic, 0, 30) * 0.25
        + scale(f.roe, 0, 40) * 0.2
    )

    # Valuation: cheaper multiples score higher (inverted).
    valuation = (
        (100 - scale(f.pe, 10, 70)) * 0.4
        + (100 - scale(f.ps, 2, 25)) * 0.3
        + (100 - scale(f.ev_ebitda, 8, 40)) * 0.3
    )

    # Financial strength: cash vs debt + FCF.
    strength = (
        scale(f.cash_debt_ratio, 0.3, 4.0) * 0.5
        + scale(f.fcf_margin, -5, 30) * 0.3
        + scale(f.operating_margin, 0, 40) * 0.2
    )

    # Blended fundamental score leans on growth + quality.
    fundamental = growth * 0.45 + quality * 0.35 + valuation * 0.20

    return FundamentalScores(
        fundamental_score=round(clamp(fundamental), 1),
        quality_score=round(clamp(quality), 1),
        valuation_score=round(clamp(valuation), 1),
        financial_strength_score=round(clamp(strength), 1),
    )
