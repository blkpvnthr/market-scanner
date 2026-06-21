"""IPO scoring: overall IPO score plus momentum and quality sub-scores.

Names that are neither recent nor upcoming IPOs receive a neutral score so the
component does not distort the blend for seasoned companies.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import IPOFeatures
from ._util import clamp, scale


@dataclass
class IPOScores:
    ipo_score: float = 50.0
    ipo_momentum_score: float = 50.0
    ipo_quality_score: float = 50.0
    applies: bool = False


def score_ipo(i: IPOFeatures) -> IPOScores:
    if not (i.is_recent or i.is_upcoming):
        return IPOScores(applies=False)

    # Momentum from post-IPO performance (recent IPOs only).
    momentum = (
        scale(i.perf_30d, -20, 50) * 0.3
        + scale(i.perf_90d, -30, 90) * 0.4
        + scale(i.perf_180d, -40, 150) * 0.3
    ) if i.is_recent else 60.0  # upcoming: speculative-positive default

    # Quality from growth + scale.
    quality = (
        scale(i.revenue_growth, 10, 100) * 0.7
        + scale(i.market_cap, 1e9, 4e10) * 0.3
    )

    overall = clamp(momentum * 0.55 + quality * 0.45)
    return IPOScores(
        ipo_score=round(overall, 1),
        ipo_momentum_score=round(clamp(momentum), 1),
        ipo_quality_score=round(clamp(quality), 1),
        applies=True,
    )
