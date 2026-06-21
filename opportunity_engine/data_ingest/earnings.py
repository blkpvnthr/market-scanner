"""Earnings facade. Delegates to the active provider.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import EarningsFeatures
from .base import DataProvider


def get_earnings(provider: DataProvider, ticker: str) -> EarningsFeatures:
    return provider.get_earnings(ticker) or EarningsFeatures()
