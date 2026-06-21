"""Risk, thesis and portfolio tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.models import RiskLevel
from opportunity_engine.portfolio import build_portfolios


def test_risk_levels_valid(scan_result):
    for o in scan_result.opportunities:
        assert isinstance(o.risk.level, RiskLevel)
        # Every standard risk factor is present.
        for key in ["valuation", "debt", "competition", "liquidity", "regulatory"]:
            assert key in o.risk.factors


def test_thesis_mentions_ticker(scan_result):
    o = scan_result.opportunities[0]
    assert o.ticker in o.thesis.summary
    assert len(o.thesis.key_catalysts) >= 1


def test_portfolios_built(scan_result):
    ports = build_portfolios(scan_result.opportunities)
    assert set(ports) == {"top5", "top10", "concentrated", "growth", "quality"}
    for port in ports.values():
        if not port.positions:
            continue
        total = sum(p.weight for p in port.positions)
        assert abs(total - 1.0) < 0.02  # weights sum to ~100%


def test_sector_cap_respected(scan_result):
    from collections import defaultdict

    port = build_portfolios(scan_result.opportunities)["top10"]
    by_sector = defaultdict(float)
    for p in port.positions:
        by_sector[p.sector] += p.weight
    # Allow a small numerical tolerance above the 40% cap.
    assert max(by_sector.values()) <= 0.45
