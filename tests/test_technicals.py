"""Technical indicator tests. Research only. Not financial advice."""

from __future__ import annotations

from datetime import date, timedelta

from opportunity_engine.features import technicals as T
from opportunity_engine.features.technicals import compute_technicals
from opportunity_engine.models import PriceBar, PriceHistory


def _linear_history(n: int = 220, start: float = 100.0, step: float = 1.0) -> PriceHistory:
    bars = []
    d = date(2025, 1, 1)
    price = start
    for i in range(n):
        o = price
        c = price + step
        bars.append(PriceBar(d + timedelta(days=i), o, c + 0.5, o - 0.5, c, 1_000_000))
        price = c
    return PriceHistory("LIN", bars)


def test_sma_matches_mean():
    vals = [float(i) for i in range(1, 21)]
    assert T.sma(vals, 20) == sum(vals) / 20
    assert T.sma(vals, 50) is None  # not enough data


def test_rsi_uptrend_is_high():
    closes = [float(i) for i in range(1, 40)]
    rsi = T.rsi(closes, 14)
    assert rsi is not None and rsi > 95  # pure uptrend -> RSI ~100


def test_returns_and_levels():
    hist = _linear_history()
    tf = compute_technicals(hist)
    assert tf.sma20 is not None and tf.sma50 is not None and tf.sma200 is not None
    assert tf.ret_5d is not None and tf.ret_5d > 0
    assert tf.rsi is not None
    # Stacked uptrend -> strong trend score.
    assert tf.trend_score >= 60
    assert tf.atr is not None and tf.atr > 0


def test_short_history_degrades_gracefully():
    bars = [PriceBar(date(2025, 1, 1), 10, 11, 9, 10, 1000)]
    tf = compute_technicals(PriceHistory("X", bars))
    assert tf.sma200 is None
    assert tf.volatility_score >= 0


def test_relative_volume():
    vols = [100.0] * 21 + [300.0]
    assert T.relative_volume(vols, 20) == 3.0
