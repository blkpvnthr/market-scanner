"""Entry/exit engine tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.data_ingest.mock_provider import MockProvider
from opportunity_engine.engine.entry_exit_engine import build_plan
from opportunity_engine.features import compute_technicals


def _plan(ticker: str):
    p = MockProvider(seed=7)
    hist = p.get_price_history(ticker, 260)
    tf = compute_technicals(hist)
    return build_plan(hist.last_close, tf, p.get_analyst_targets(ticker))


def test_entry_ordering():
    plan = _plan("NVDA")
    # Aggressive (breakout) is highest, conservative (pullback) lowest.
    assert plan.aggressive_entry >= plan.base_entry >= plan.conservative_entry
    # Stop sits below all entries.
    assert plan.stop_loss < plan.conservative_entry


def test_targets_monotonic():
    plan = _plan("AMD")
    assert plan.target_1 < plan.target_2 < plan.target_3


def test_risk_reward_positive():
    plan = _plan("ASML")
    assert plan.risk_reward_ratio > 0
    assert plan.max_drawdown_estimate < 0  # stop below price -> negative DD


def test_zero_price_safe():
    from opportunity_engine.models import AnalystTargets, TechnicalFeatures

    plan = build_plan(0.0, TechnicalFeatures(), AnalystTargets())
    assert plan.current_price == 0.0
