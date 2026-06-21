"""Yahoo Finance provider (Phase 2).

Backed by the optional ``yfinance`` package. Supplies price history,
company/sector metadata, fundamentals and analyst targets where available.
Returns ``None`` for anything missing so the fallback (mock) fills the gap.
No API key required.

Research only. Not financial advice.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from ..models import (
    AnalystTargets,
    FundamentalFeatures,
    PriceBar,
    PriceHistory,
)
from .base import DataProvider


class YahooProvider(DataProvider):
    name = "yahoo"

    def __init__(self) -> None:
        self._yf = None
        try:  # import lazily so the engine never hard-depends on it
            import yfinance as yf  # type: ignore

            self._yf = yf
        except Exception:
            self._yf = None
        self._cache: dict[str, object] = {}

    def available(self) -> bool:
        return self._yf is not None

    def _ticker(self, symbol: str):
        if symbol not in self._cache:
            self._cache[symbol] = self._yf.Ticker(symbol)  # type: ignore[union-attr]
        return self._cache[symbol]

    def get_price_history(self, ticker: str, days: int = 260) -> Optional[PriceHistory]:
        if not self.available():
            return None
        try:
            period = "2y" if days > 252 else "1y"
            df = self._ticker(ticker).history(period=period, auto_adjust=False)
            if df is None or df.empty:
                return None
            bars = []
            for idx, row in df.tail(days).iterrows():
                d = idx.date() if hasattr(idx, "date") else date.today()
                bars.append(PriceBar(d, float(row["Open"]), float(row["High"]),
                                     float(row["Low"]), float(row["Close"]),
                                     float(row["Volume"])))
            return PriceHistory(ticker, bars) if bars else None
        except Exception:
            return None

    def _info(self, ticker: str) -> dict:
        try:
            info = getattr(self._ticker(ticker), "info", None)
            return info if isinstance(info, dict) else {}
        except Exception:
            return {}

    def get_company_name(self, ticker: str) -> Optional[str]:
        return self._info(ticker).get("longName") or self._info(ticker).get("shortName")

    def get_sector(self, ticker: str) -> Optional[str]:
        return self._info(ticker).get("sector")

    def get_fundamentals(self, ticker: str) -> Optional[FundamentalFeatures]:
        info = self._info(ticker)
        if not info:
            return None

        def pct(key: str) -> Optional[float]:
            v = info.get(key)
            return round(v * 100, 1) if isinstance(v, (int, float)) else None

        return FundamentalFeatures(
            revenue_growth=pct("revenueGrowth"),
            eps_growth=pct("earningsGrowth"),
            gross_margin=pct("grossMargins"),
            operating_margin=pct("operatingMargins"),
            fcf_margin=None,
            cash=info.get("totalCash"),
            debt=info.get("totalDebt"),
            cash_debt_ratio=(round(info["totalCash"] / info["totalDebt"], 2)
                             if info.get("totalDebt") else None),
            roe=pct("returnOnEquity"),
            pe=info.get("trailingPE"),
            ps=info.get("priceToSalesTrailing12Months"),
            institutional_ownership=pct("heldPercentInstitutions"),
            insider_ownership=pct("heldPercentInsiders"),
        )

    def get_analyst_targets(self, ticker: str) -> Optional[AnalystTargets]:
        info = self._info(ticker)
        if not info or not info.get("targetMeanPrice"):
            return None
        return AnalystTargets(
            target_low=info.get("targetLowPrice"),
            target_mean=info.get("targetMeanPrice"),
            target_high=info.get("targetHighPrice"),
            num_analysts=info.get("numberOfAnalystOpinions", 0) or 0,
            recommendation_trend={},
        )
