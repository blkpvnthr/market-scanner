"""IPO calendar facade. Delegates to the active provider.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import IPOFeatures
from .base import DataProvider


def get_ipo(provider: DataProvider, ticker: str) -> IPOFeatures:
    return provider.get_ipo(ticker) or IPOFeatures()
