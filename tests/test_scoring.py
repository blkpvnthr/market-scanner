"""Scoring engine tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.config import DEFAULT_WEIGHTS
from opportunity_engine.data_ingest.mock_provider import MockProvider
from opportunity_engine.engine.scorer import compute_scores
from opportunity_engine.features import compute_technicals


def _score_for(ticker: str):
    p = MockProvider(seed=7)
    hist = p.get_price_history(ticker, 260)
    tf = compute_technicals(hist)
    return compute_scores(
        technicals=tf,
        fundamentals=p.get_fundamentals(ticker),
        earnings=p.get_earnings(ticker),
        ipo=p.get_ipo(ticker),
        analyst=p.get_analyst_targets(ticker),
        catalyst=p.get_catalysts(ticker),
        sector=p.get_sector(ticker),
        current_price=hist.last_close,
        weights=dict(DEFAULT_WEIGHTS),
    )


def test_final_score_in_range():
    res = _score_for("NVDA")
    s = res.scores
    assert 0.0 <= s.final_score <= 100.0
    for v in [s.technical_score, s.fundamental_score, s.quality_score,
              s.catalyst_score, s.earnings_score, s.analyst_score, s.risk_score]:
        assert 0.0 <= v <= 100.0


def test_weights_normalized():
    res = _score_for("NVDA")
    # weights are rounded to 4dp for display, so allow a small tolerance
    assert abs(sum(res.scores.weights.values()) - 1.0) < 1e-3


def test_ipo_weight_dropped_for_seasoned_name():
    res = _score_for("MSFT")  # not an IPO
    assert not res.ipo_applies
    assert "ipo" not in res.scores.weights
    assert res.scores.ipo_score == 0.0


def test_ipo_applies_for_recent_ipo():
    res = _score_for("RKLB")  # recent IPO in the mock world
    assert res.ipo_applies
    assert "ipo" in res.scores.weights


def test_deterministic():
    a = _score_for("AMD").scores.final_score
    b = _score_for("AMD").scores.final_score
    assert a == b
