"""Alpaca market-data provider (Phase 2).

Supplies daily OHLCV bars via the optional ``alpaca-py`` package using the keys
``APCA_API_KEY`` / ``APCA_SECRET_KEY``. Data-only; no trading endpoints are
used. Returns ``None`` when keys or the library are missing.

Research only. Not financial advice.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from ..models import PriceBar, PriceHistory
from .base import DataProvider


class AlpacaProvider(DataProvider):
    name = "alpaca"

    def __init__(self, key: Optional[str], secret: Optional[str], feed: str = "iex") -> None:
        self.key = key
        self.secret = secret
        self.feed = feed
        self._client = None
        if key and secret:
            try:
                from alpaca.data.historical import StockHistoricalDataClient  # type: ignore

                self._client = StockHistoricalDataClient(key, secret)
            except Exception:
                self._client = None

    def available(self) -> bool:
        return self._client is not None

    def get_price_history(self, ticker: str, days: int = 260) -> Optional[PriceHistory]:
        if not self.available():
            return None
        try:
            from alpaca.data.requests import StockBarsRequest  # type: ignore
            from alpaca.data.timeframe import TimeFrame  # type: ignore

            req = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=TimeFrame.Day,
                start=date.today() - timedelta(days=int(days * 1.6)),
                feed=self.feed,
            )
            bars_set = self._client.get_stock_bars(req)  # type: ignore[union-attr]
            rows = bars_set.data.get(ticker, []) if hasattr(bars_set, "data") else []
            bars = [
                PriceBar(b.timestamp.date(), float(b.open), float(b.high),
                         float(b.low), float(b.close), float(b.volume))
                for b in rows
            ]
            return PriceHistory(ticker, bars[-days:]) if bars else None
        except Exception:
            return None
