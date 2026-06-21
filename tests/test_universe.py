"""Universe construction tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.config import Settings
from opportunity_engine.engine.universe import UPCOMING_IPOS, build_universe


def test_upcoming_ipo_placeholders_only_in_mock():
    """Fake pre-listing tickers (STRIPE, CHIME, …) must not enter a live universe
    where they would 404, but should appear in the mock world for the demo."""
    placeholders = {t.upper() for t in UPCOMING_IPOS}

    mock_u = {e.ticker for e in build_universe(Settings(provider="mock", max_universe=200))}
    assert placeholders & mock_u, "expected upcoming-IPO placeholders in mock universe"

    live_u = {e.ticker for e in build_universe(Settings(provider="yahoo", max_universe=200))}
    assert not (placeholders & live_u), "live universe must exclude IPO placeholders"


def test_recent_ipos_are_real_tickers_and_always_present():
    # RKLB/LUNR/ASTS/ALAB are real, resolvable symbols -> kept in live mode too.
    live_u = {e.ticker for e in build_universe(Settings(provider="yahoo", max_universe=200))}
    for t in ("RKLB", "LUNR", "ASTS", "ALAB"):
        assert t in live_u
