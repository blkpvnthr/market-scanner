"""Catalyst scoring.

Turns the raw catalyst/news bundle into a 0..100 catalyst score and fills in the
aggregate confidence / timing / impact fields. Guarantees that at least one
catalyst is present for every name (an earnings catalyst is synthesized if the
provider returned none).

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import Catalyst, CatalystFeatures, CatalystType
from ._util import clamp, scale

# Relative weight of each catalyst category towards the score.
TYPE_WEIGHT: dict[CatalystType, float] = {
    CatalystType.AI: 1.0,
    CatalystType.SEMICONDUCTORS: 0.95,
    CatalystType.FDA_APPROVAL: 1.0,
    CatalystType.GOVERNMENT_CONTRACTS: 0.85,
    CatalystType.DEFENSE: 0.8,
    CatalystType.SPACE: 0.8,
    CatalystType.MA: 0.9,
    CatalystType.PRODUCT_LAUNCH: 0.75,
    CatalystType.EARNINGS: 0.7,
    CatalystType.INDEX_INCLUSION: 0.7,
    CatalystType.IPO_MOMENTUM: 0.75,
    CatalystType.INSIDER_BUYING: 0.65,
    CatalystType.BUYBACKS: 0.6,
    CatalystType.RATE_CUTS: 0.55,
    CatalystType.MACRO: 0.5,
}


def _ensure_minimum(cat: CatalystFeatures) -> None:
    if not cat.catalysts:
        cat.catalysts.append(
            Catalyst(
                CatalystType.EARNINGS,
                "Upcoming quarterly earnings report",
                confidence=0.5,
                timing="Within ~1 quarter",
                impact=0.5,
                source="synthesized",
            )
        )


def score_catalysts(cat: CatalystFeatures) -> CatalystFeatures:
    """Populate catalyst_score / confidence / timing / impact in place and
    return the same object (so callers can use the return value fluently)."""
    _ensure_minimum(cat)

    # Strongest catalyst by weight * confidence * impact.
    def strength(c: Catalyst) -> float:
        return TYPE_WEIGHT.get(c.type, 0.5) * c.confidence * (0.5 + 0.5 * c.impact)

    ranked = sorted(cat.catalysts, key=strength, reverse=True)
    top = ranked[0]

    breadth = clamp(len(cat.catalysts) * 12, 0, 45)          # more catalysts -> higher
    quality = strength(top) * 100 * 0.55
    velocity = scale(cat.news_velocity, 0.2, 5.0) * 0.18
    sentiment = (cat.sentiment_score + 1) / 2 * 100 * 0.12

    cat.catalyst_score = round(clamp(breadth * 0.35 + quality + velocity + sentiment), 1)
    cat.catalyst_confidence = round(top.confidence, 2)
    cat.catalyst_timing = top.timing
    cat.catalyst_impact = round(top.impact, 2)
    return cat
