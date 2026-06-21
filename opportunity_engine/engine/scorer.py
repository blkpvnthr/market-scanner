"""Scoring engine.

Calls every component scorer, then blends them into a transparent 0..100 final
score using the configured weights. Every sub-score is preserved on the returned
:class:`~opportunity_engine.models.ScoreBreakdown` so the result is fully
explainable. The IPO component only participates for genuine IPO names; its
weight is redistributed otherwise so seasoned companies are not penalised.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..features import (
    assess_risk,
    score_analyst,
    score_catalysts,
    score_earnings,
    score_fundamentals,
    score_ipo,
)
from ..models import (
    AnalystTargets,
    CatalystFeatures,
    EarningsFeatures,
    FundamentalFeatures,
    IPOFeatures,
    RiskAssessment,
    ScoreBreakdown,
    TechnicalFeatures,
)


@dataclass
class ScoringResult:
    scores: ScoreBreakdown
    risk: RiskAssessment
    valuation_score: float
    financial_strength_score: float
    ipo_applies: bool


def compute_scores(
    *,
    technicals: TechnicalFeatures,
    fundamentals: FundamentalFeatures,
    earnings: EarningsFeatures,
    ipo: IPOFeatures,
    analyst: AnalystTargets,
    catalyst: CatalystFeatures,
    sector: str,
    current_price: float,
    weights: dict[str, float],
) -> ScoringResult:
    # Component scores.
    technical_score = round(
        technicals.trend_score * 0.5
        + technicals.breakout_score * 0.3
        + technicals.reversal_score * 0.2,
        1,
    )
    fnd = score_fundamentals(fundamentals)
    catalyst = score_catalysts(catalyst)  # populates aggregate fields in place
    earn = score_earnings(earnings)
    ipo_s = score_ipo(ipo)
    analyst_score = score_analyst(analyst, current_price)
    risk = assess_risk(fundamentals, technicals, ipo, sector)

    # Effective weights: drop IPO weight when it does not apply and renormalise.
    w = dict(weights)
    if not ipo_s.applies:
        w.pop("ipo", None)
    total_w = sum(w.values()) or 1.0

    parts = {
        "technical": technical_score,
        "fundamental": fnd.fundamental_score,
        "quality": fnd.quality_score,
        "catalyst": catalyst.catalyst_score,
        "earnings": earn.earnings_score,
        "ipo": ipo_s.ipo_score,
        "analyst": analyst_score,
        "risk": risk.risk_score,
    }
    final = sum(parts[k] * w[k] for k in w) / total_w

    breakdown = ScoreBreakdown(
        technical_score=technical_score,
        fundamental_score=fnd.fundamental_score,
        quality_score=fnd.quality_score,
        catalyst_score=catalyst.catalyst_score,
        earnings_score=earn.earnings_score,
        ipo_score=ipo_s.ipo_score if ipo_s.applies else 0.0,
        analyst_score=analyst_score,
        risk_score=risk.risk_score,
        final_score=round(final, 1),
        weights={k: round(v / total_w, 4) for k, v in w.items()},
    )

    return ScoringResult(
        scores=breakdown,
        risk=risk.assessment,
        valuation_score=fnd.valuation_score,
        financial_strength_score=fnd.financial_strength_score,
        ipo_applies=ipo_s.applies,
    )
