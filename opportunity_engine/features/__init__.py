"""Feature computation layer: technicals and component scores.

Research only. Not financial advice.
"""

from .technicals import compute_technicals
from .fundamental_score import score_fundamentals
from .catalyst_score import score_catalysts
from .earnings_score import score_earnings
from .ipo_score import score_ipo
from .analyst_score import score_analyst
from .risk_score import assess_risk

__all__ = [
    "compute_technicals",
    "score_fundamentals",
    "score_catalysts",
    "score_earnings",
    "score_ipo",
    "score_analyst",
    "assess_risk",
]
