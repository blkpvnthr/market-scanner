"""Alpha Vantage provider (Phase 2, optional).

Uses the REST API via ``requests`` and ``ALPHA_VANTAGE_API_KEY``. Supplies daily
price history and basic fundamentals. The free tier is heavily rate limited, so
this provider is best used for a small universe; it degrades to ``None`` on any
error or throttle.

Research only. Not financial advice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..models import FundamentalFeatures, PriceBar, PriceHistory
from .base import DataProvider

_BASE = "https://www.alphavantage.co/query"


class AlphaVantageProvider(DataProvider):
    name = "alpha_vantage"

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        self._requests = None
        if api_key:
            try:
                import requests  # type: ignore

                self._requests = requests
            except Exception:
                self._requests = None

    def available(self) -> bool:
        return bool(self.api_key and self._requests)

    def _get(self, **params) -> Optional[dict]:
        if not self.available():
            return None
        try:
            params["apikey"] = self.api_key
            resp = self._requests.get(_BASE, params=params, timeout=10)  # type: ignore[union-attr]
            if resp.status_code != 200:
                return None
            data = resp.json()
            if "Note" in data or "Information" in data:  # rate limited
                return None
            return data
        except Exception:
            return None

    def get_price_history(self, ticker: str, days: int = 260) -> Optional[PriceHistory]:
        data = self._get(function="TIME_SERIES_DAILY", symbol=ticker, outputsize="full")
        series = (data or {}).get("Time Series (Daily)")
        if not series:
            return None
        bars = []
        for ds, row in sorted(series.items()):
            try:
                bars.append(PriceBar(
                    datetime.strptime(ds, "%Y-%m-%d").date(),
                    float(row["1. open"]), float(row["2. high"]),
                    float(row["3. low"]), float(row["4. close"]),
                    float(row["5. volume"]),
                ))
            except Exception:
                continue
        return PriceHistory(ticker, bars[-days:]) if bars else None

    def get_fundamentals(self, ticker: str) -> Optional[FundamentalFeatures]:
        data = self._get(function="OVERVIEW", symbol=ticker)
        if not data or "Symbol" not in data:
            return None

        def num(key: str, mult: float = 1.0) -> Optional[float]:
            try:
                v = data.get(key)
                return round(float(v) * mult, 2) if v not in (None, "None", "-") else None
            except Exception:
                return None

        return FundamentalFeatures(
            gross_margin=num("GrossProfitTTM"),
            operating_margin=num("OperatingMarginTTM", 100),
            roe=num("ReturnOnEquityTTM", 100),
            pe=num("PERatio"),
            ps=num("PriceToSalesRatioTTM"),
            ev_ebitda=num("EVToEBITDA"),
        )
