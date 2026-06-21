"""Earnings scoring: an overall earnings-quality score plus an earnings-as-
catalyst score that rises as a high-quality print approaches.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from ..models import EarningsFeatures
from ._util import clamp, scale


@dataclass
class EarningsScores:
    earnings_score: float = 50.0
    earnings_catalyst_score: float = 50.0


def score_earnings(e: EarningsFeatures) -> EarningsScores:
    # Average historical surprise.
    if e.surprises:
        avg_surprise = mean(s.surprise_pct for s in e.surprises)
        beats = sum(1 for s in e.surprises if s.surprise_pct > 0) / len(e.surprises)
    else:
        avg_surprise, beats = 0.0, 0.5

    quality = (
        scale(avg_surprise, -5, 15) * 0.4
        + beats * 100 * 0.3
        + scale(e.guidance_revision, -8, 12) * 0.2
        + scale(e.post_earnings_drift, -5, 10) * 0.1
    )

    # Catalyst score: stronger when a quality print is near (but not too near to
    # be already priced) — peaks ~1-3 weeks out.
    proximity = 50.0
    if e.days_until_earnings is not None:
        d = e.days_until_earnings
        if d <= 0:
            proximity = 40.0
        elif d <= 21:
            proximity = 90.0 - (21 - d) * 0.5
        else:
            proximity = clamp(90.0 - (d - 21) * 1.2, 30, 90)
    catalyst = clamp(proximity * 0.6 + quality * 0.4)

    return EarningsScores(
        earnings_score=round(clamp(quality), 1),
        earnings_catalyst_score=round(catalyst, 1),
    )
