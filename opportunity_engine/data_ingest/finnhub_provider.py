"""Finnhub provider (Phase 2, optional).

Uses the REST API directly via ``requests`` (no SDK needed) and the
``FINNHUB_API_KEY`` env var. Supplies fundamentals, analyst targets, earnings
and news/catalysts where the free tier allows. Degrades to ``None`` on any
error or missing key.

Research only. Not financial advice.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ..models import (
    AnalystTargets,
    Catalyst,
    CatalystFeatures,
    CatalystType,
    NewsItem,
)
from .base import DataProvider

_BASE = "https://finnhub.io/api/v1"


class FinnhubProvider(DataProvider):
    name = "finnhub"

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

    def get_price_history(self, ticker: str, days: int = 260):  # not used; candles are premium
        return None

    def _get(self, path: str, **params) -> Optional[dict]:
        if not self.available():
            return None
        try:
            params["token"] = self.api_key
            resp = self._requests.get(f"{_BASE}{path}", params=params, timeout=8)  # type: ignore[union-attr]
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def get_analyst_targets(self, ticker: str) -> Optional[AnalystTargets]:
        data = self._get("/stock/price-target", symbol=ticker)
        rec = self._get("/stock/recommendation", symbol=ticker)
        if not data or not data.get("targetMean"):
            return None
        trend: dict[str, int] = {}
        if isinstance(rec, list) and rec:
            latest = rec[0]
            trend = {
                "buy": int(latest.get("strongBuy", 0)) + int(latest.get("buy", 0)),
                "hold": int(latest.get("hold", 0)),
                "sell": int(latest.get("sell", 0)) + int(latest.get("strongSell", 0)),
            }
        return AnalystTargets(
            target_low=data.get("targetLow"),
            target_mean=data.get("targetMean"),
            target_high=data.get("targetHigh"),
            num_analysts=int(data.get("numberAnalysts", 0) or 0),
            recommendation_trend=trend,
        )

    def get_catalysts(self, ticker: str) -> Optional[CatalystFeatures]:
        today = date.today()
        frm = today.replace(year=today.year - 1) if today.month == 2 and today.day == 29 else \
            today.replace(day=1)
        data = self._get("/company-news", symbol=ticker,
                         **{"from": str(today.replace(day=1)), "to": str(today)})
        if not isinstance(data, list) or not data:
            return None
        news = []
        for item in data[:25]:
            try:
                dt = datetime.fromtimestamp(item.get("datetime", 0)).date()
            except Exception:
                dt = today
            news.append(NewsItem(headline=item.get("headline", ""),
                                 summary=item.get("summary", ""),
                                 source=item.get("source", "finnhub"),
                                 url=item.get("url", ""), dt=dt))
        cf = CatalystFeatures(news_count=len(data),
                              news_velocity=round(len(data) / 30.0, 2),
                              news=news)
        # Always seed at least one catalyst from news flow.
        cf.catalysts.append(Catalyst(CatalystType.PRODUCT_LAUNCH,
                                     "Recent news flow / company announcements",
                                     confidence=0.5, timing="Ongoing", impact=0.5,
                                     source="finnhub-news"))
        return cf
