"""Ranking.

Sorts opportunities by final score (with deterministic tie-breakers) and assigns
1-based ranks. Returns the full ranked list; callers slice the top-N.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import Opportunity


def rank_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    ranked = sorted(
        opportunities,
        key=lambda o: (
            o.scores.final_score,
            o.scores.catalyst_score,
            o.scores.risk_score,
            o.ticker,
        ),
        reverse=True,
    )
    for i, opp in enumerate(ranked, start=1):
        opp.rank = i
    return ranked
