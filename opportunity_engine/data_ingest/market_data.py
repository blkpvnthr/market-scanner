"""Market-data facade: price history + derived spot price/metadata.

Delegates to the active :class:`DataProvider`. Research only. Not financial advice.
"""

from __future__ import annotations

from typing import Optional

from ..models import PriceHistory
from .base import DataProvider


def get_price_history(provider: DataProvider, ticker: str, days: int = 260) -> Optional[PriceHistory]:
    return provider.get_price_history(ticker, days)


def get_current_price(provider: DataProvider, ticker: str, days: int = 260) -> float:
    hist = provider.get_price_history(ticker, days)
    return hist.last_close if hist else 0.0


def get_company_name(provider: DataProvider, ticker: str) -> str:
    return provider.get_company_name(ticker) or f"{ticker} Inc."


def get_sector(provider: DataProvider, ticker: str) -> str:
    return provider.get_sector(ticker) or "Diversified"
