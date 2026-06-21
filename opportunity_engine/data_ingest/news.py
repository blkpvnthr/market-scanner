"""News & catalyst facade. Delegates to the active provider.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import CatalystFeatures
from .base import DataProvider


def get_catalysts(provider: DataProvider, ticker: str) -> CatalystFeatures:
    return provider.get_catalysts(ticker) or CatalystFeatures()
