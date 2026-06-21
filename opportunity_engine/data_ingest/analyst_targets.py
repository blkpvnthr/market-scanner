"""Analyst targets facade. Delegates to the active provider.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import AnalystTargets
from .base import DataProvider


def get_analyst_targets(provider: DataProvider, ticker: str) -> AnalystTargets:
    return provider.get_analyst_targets(ticker) or AnalystTargets()
