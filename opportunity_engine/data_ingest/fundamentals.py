"""Fundamentals facade. Delegates to the active provider.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import FundamentalFeatures
from .base import DataProvider


def get_fundamentals(provider: DataProvider, ticker: str) -> FundamentalFeatures:
    return provider.get_fundamentals(ticker) or FundamentalFeatures()
