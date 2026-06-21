"""Data ingestion layer and provider registry.

``build_provider`` returns the active :class:`DataProvider` for a given
:class:`~opportunity_engine.config.Settings`. Real providers are always composed
with the deterministic mock as a fallback so every field is populated and the
scan never fails on a missing key.

Selection (``settings.provider``):
  * ``mock``           – mock only (default for offline/Phase-1 runs)
  * ``auto``           – mock only, unless a key is present and OE_PROVIDER set
  * ``yahoo``          – Yahoo Finance (yfinance) + mock fallback
  * ``alpaca``         – Alpaca data + mock fallback
  * ``finnhub``        – Finnhub + mock fallback
  * ``alpha_vantage``  – Alpha Vantage + mock fallback

Research only. Not financial advice.
"""

from __future__ import annotations

from ..config import Settings
from .base import DataProvider, FallbackProvider
from .mock_provider import MockProvider

__all__ = ["DataProvider", "FallbackProvider", "MockProvider", "build_provider"]


def build_provider(settings: Settings) -> DataProvider:
    mock = MockProvider(seed=settings.seed)
    choice = (settings.provider or "auto").lower()

    if choice in {"mock", "auto"}:
        return mock

    primary: DataProvider
    if choice == "yahoo":
        from .yahoo_provider import YahooProvider

        primary = YahooProvider()
    elif choice == "alpaca":
        from .alpaca_provider import AlpacaProvider

        primary = AlpacaProvider(settings.alpaca_key, settings.alpaca_secret,
                                 settings.alpaca_data_feed)
    elif choice == "finnhub":
        from .finnhub_provider import FinnhubProvider

        primary = FinnhubProvider(settings.finnhub_key)
    elif choice == "alpha_vantage":
        from .alpha_vantage_provider import AlphaVantageProvider

        primary = AlphaVantageProvider(settings.alpha_vantage_key)
    else:
        return mock

    if not primary.available():
        # Key/library missing -> graceful degradation to mock.
        return mock
    return FallbackProvider(primary, mock)
