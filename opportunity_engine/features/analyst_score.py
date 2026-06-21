"""Analyst conviction scoring.

Higher when: large analyst coverage, net upward revisions, and large upside to
the consensus (mean) target.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import AnalystTargets
from ._util import clamp, scale


def score_analyst(a: AnalystTargets, current_price: float) -> float:
    coverage = scale(a.num_analysts, 3, 40)

    revisions = scale(a.recent_revisions, -5, 8)

    upside = 50.0
    if current_price > 0 and a.target_mean:
        upside_pct = (a.target_mean - current_price) / current_price * 100.0
        upside = scale(upside_pct, -10, 40)

    # Buy ratio from recommendation trend.
    trend = a.recommendation_trend or {}
    total = sum(trend.values())
    buy_ratio = (trend.get("buy", 0) / total * 100.0) if total else 50.0

    score = coverage * 0.25 + revisions * 0.2 + upside * 0.4 + buy_ratio * 0.15
    return round(clamp(score), 1)
