"""Provenance, data-flag and validation tests. Research only. Not financial advice."""

from __future__ import annotations

from datetime import date, timedelta

from opportunity_engine.config import Settings
from opportunity_engine.data_ingest import build_provider
from opportunity_engine.data_ingest.base import FallbackProvider
from opportunity_engine.data_ingest.mock_provider import MockProvider
from opportunity_engine.engine.pipeline import STALE_WINDOW_DAYS, fetch_all
from opportunity_engine.engine.validate import validate_ticker
from opportunity_engine.models import DataFlag


def test_mock_scan_flags_mock_data(scan_result):
    for o in scan_result.opportunities:
        assert o.provenance.flags == [DataFlag.MOCK_DATA.value]
        assert o.provenance.fallback_used is False
        assert o.provenance.price_source == "mock"
        assert not o.provenance.missing_fields


def test_fallback_provider_reports_live_source():
    """A fake live provider supplying only price should be tagged live for price
    and fall back to mock for everything else (PARTIAL_LIVE_DATA)."""

    class PriceOnly(MockProvider):
        name = "fake_live"

        def available(self) -> bool:
            return True

        def get_fundamentals(self, ticker):
            return None

        def get_earnings(self, ticker):
            return None

        def get_ipo(self, ticker):
            return None

        def get_analyst_targets(self, ticker):
            return None

        def get_catalysts(self, ticker):
            return None

        def get_company_name(self, ticker):
            return None

        def get_sector(self, ticker):
            return None

    provider = FallbackProvider(PriceOnly(seed=7), MockProvider(seed=7))
    settings = Settings(provider="mock", seed=7)
    data = fetch_all(provider, "NVDA", settings, today=date(2026, 6, 20))
    assert data is not None
    assert data.provenance.price_source == "fake_live"
    assert data.provenance.fundamentals_source == "mock"
    assert data.provenance.fallback_used is True
    assert DataFlag.PARTIAL_LIVE_DATA.value in data.provenance.flags
    assert DataFlag.MISSING_ANALYST_TARGETS.value in data.provenance.flags


def test_stale_detection():
    """If the live price bar is older than the window, STALE_DATA is flagged."""

    class StaleLive(MockProvider):
        name = "stale_live"

        def available(self) -> bool:
            return True

    provider = FallbackProvider(StaleLive(seed=7), MockProvider(seed=7))
    settings = Settings(provider="mock", seed=7)
    # Mock bars end 2026-06-19; choose a 'today' far past the stale window.
    far_future = date(2026, 6, 19) + timedelta(days=STALE_WINDOW_DAYS + 10)
    data = fetch_all(provider, "NVDA", settings, today=far_future)
    assert DataFlag.STALE_DATA.value in data.provenance.flags
    assert data.provenance.stale_warnings


def test_validate_mock_readiness():
    settings = Settings(provider="mock", seed=7)
    provider = build_provider(settings)
    report = validate_ticker(provider, "ASML", settings)
    assert report.ok
    assert report.readiness == 60.0  # complete but synthetic
    assert all(src == "mock" for src in report.sources.values())
    assert report.flags == [DataFlag.MOCK_DATA.value]
