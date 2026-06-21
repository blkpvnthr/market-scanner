"""Shared fixtures. Research only. Not financial advice."""

from __future__ import annotations

import pytest

from opportunity_engine.config import Settings
from opportunity_engine.data_ingest.mock_provider import MockProvider
from opportunity_engine.engine.pipeline import run_scan


@pytest.fixture
def settings() -> Settings:
    return Settings(provider="mock", top_n=10, max_universe=40, seed=7)


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider(seed=7)


@pytest.fixture
def scan_result(settings):
    return run_scan(settings)
