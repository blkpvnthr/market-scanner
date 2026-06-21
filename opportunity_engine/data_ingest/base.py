"""Data provider abstraction.

A `DataProvider` returns typed feature bundles for a ticker. Concrete providers
(mock, Alpaca, Finnhub, Yahoo, Alpha Vantage) implement as much as they can and
return ``None`` / empty bundles for anything they cannot supply. The engine
always composes a provider with the mock as a fallback so every field is
populated and the scan never crashes on a missing key.

Research only. Not financial advice.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from ..models import (
    AnalystTargets,
    CatalystFeatures,
    EarningsFeatures,
    FundamentalFeatures,
    IPOFeatures,
    PriceHistory,
)


@dataclass
class FetchResult:
    """A fetched value plus the provenance of where it came from."""
    value: Any
    source: str            # provider name that supplied the value ("mock" if synthesized)
    fallback_used: bool    # True when a live primary was available but yielded nothing
    primary_available: bool


class DataProvider(ABC):
    """Interface every data source implements."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Return True when this provider is usable (keys/libs present)."""

    @abstractmethod
    def get_price_history(self, ticker: str, days: int = 260) -> Optional[PriceHistory]:
        ...

    def get_company_name(self, ticker: str) -> Optional[str]:
        return None

    def get_sector(self, ticker: str) -> Optional[str]:
        return None

    def get_fundamentals(self, ticker: str) -> Optional[FundamentalFeatures]:
        return None

    def get_earnings(self, ticker: str) -> Optional[EarningsFeatures]:
        return None

    def get_ipo(self, ticker: str) -> Optional[IPOFeatures]:
        return None

    def get_analyst_targets(self, ticker: str) -> Optional[AnalystTargets]:
        return None

    def get_catalysts(self, ticker: str) -> Optional[CatalystFeatures]:
        return None


class FallbackProvider(DataProvider):
    """Compose a primary provider with a fallback (typically the mock).

    Each field is taken from the primary if it returns a non-empty value,
    otherwise from the fallback. This is what gives the engine its graceful
    degradation guarantee.
    """

    name = "fallback"

    def __init__(self, primary: DataProvider, fallback: DataProvider):
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}+{fallback.name}"

    def available(self) -> bool:
        return True

    def _pick(self, method: str, ticker: str, *args):
        for prov in (self.primary, self.fallback):
            try:
                if prov is self.primary and not prov.available():
                    continue
                value = getattr(prov, method)(ticker, *args)
            except Exception:
                value = None
            if value:
                return value
        return getattr(self.fallback, method)(ticker, *args)

    def get_price_history(self, ticker: str, days: int = 260) -> Optional[PriceHistory]:
        return self._pick("get_price_history", ticker, days)

    def get_company_name(self, ticker: str) -> Optional[str]:
        return self._pick("get_company_name", ticker)

    def get_sector(self, ticker: str) -> Optional[str]:
        return self._pick("get_sector", ticker)

    def get_fundamentals(self, ticker: str) -> Optional[FundamentalFeatures]:
        return self._pick("get_fundamentals", ticker)

    def get_earnings(self, ticker: str) -> Optional[EarningsFeatures]:
        return self._pick("get_earnings", ticker)

    def get_ipo(self, ticker: str) -> Optional[IPOFeatures]:
        return self._pick("get_ipo", ticker)

    def get_analyst_targets(self, ticker: str) -> Optional[AnalystTargets]:
        return self._pick("get_analyst_targets", ticker)

    def get_catalysts(self, ticker: str) -> Optional[CatalystFeatures]:
        return self._pick("get_catalysts", ticker)

    def fetch_with_source(self, method: str, ticker: str, *args) -> FetchResult:
        """Like ``_pick`` but reports which provider supplied the value.

        Tries the primary (when available); if it yields a non-empty value the
        result is tagged with the primary's name. Otherwise the mock fallback is
        used and ``fallback_used`` is set.
        """
        primary_available = False
        try:
            primary_available = self.primary.available()
        except Exception:
            primary_available = False

        if primary_available:
            try:
                value = getattr(self.primary, method)(ticker, *args)
            except Exception:
                value = None
            if value:
                return FetchResult(value, self.primary.name, False, True)

        try:
            value = getattr(self.fallback, method)(ticker, *args)
        except Exception:
            value = None
        return FetchResult(value, self.fallback.name, primary_available, primary_available)


def fetch_sourced(provider: DataProvider, method: str, ticker: str, *args) -> FetchResult:
    """Uniform source-aware fetch that works for any provider.

    For a :class:`FallbackProvider` this delegates to its per-field tracking; for
    a plain provider (e.g. the mock) the value is tagged with that provider's
    own name and ``fallback_used`` is False.
    """
    if isinstance(provider, FallbackProvider):
        return provider.fetch_with_source(method, ticker, *args)
    try:
        value = getattr(provider, method)(ticker, *args)
    except Exception:
        value = None
    return FetchResult(value, provider.name, False, False)
