"""Technical feature computation.

Pure-Python implementations (no numpy/pandas required) so the scanner and its
tests run with zero third-party dependencies. All functions degrade gracefully
on short histories by returning ``None``.

Research only. Not financial advice.
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Optional

from ..models import PriceHistory, TechnicalFeatures


def sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period or period <= 0:
        return None
    return mean(values[-period:])


def rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = mean(gains)
    avg_loss = mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(history: PriceHistory, period: int = 14) -> Optional[float]:
    bars = history.bars
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        high, low, prev_close = bars[i].high, bars[i].low, bars[i - 1].close
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return mean(trs)


def vwap(history: PriceHistory, period: int = 20) -> Optional[float]:
    bars = history.bars[-period:]
    if not bars:
        return None
    pv = sum(((b.high + b.low + b.close) / 3.0) * b.volume for b in bars)
    vol = sum(b.volume for b in bars)
    return pv / vol if vol else None


def pct_return(closes: list[float], period: int) -> Optional[float]:
    if len(closes) <= period:
        return None
    past = closes[-period - 1]
    if past == 0:
        return None
    return (closes[-1] - past) / past * 100.0


def relative_volume(volumes: list[float], period: int = 20) -> Optional[float]:
    if len(volumes) < period + 1:
        return None
    avg = mean(volumes[-period - 1:-1])
    return volumes[-1] / avg if avg else None


def find_levels(history: PriceHistory, lookback: int = 60, window: int = 3) -> tuple[list[float], list[float]]:
    """Detect swing support (pivot lows) and resistance (pivot highs)."""
    bars = history.bars[-lookback:]
    supports, resistances = [], []
    for i in range(window, len(bars) - window):
        lo = bars[i].low
        hi = bars[i].high
        if all(lo <= bars[j].low for j in range(i - window, i + window + 1)):
            supports.append(round(lo, 2))
        if all(hi >= bars[j].high for j in range(i - window, i + window + 1)):
            resistances.append(round(hi, 2))
    # de-duplicate near-equal levels and keep the nearest few to last price
    last = history.last_close
    supports = sorted({s for s in supports if s < last}, reverse=True)[:3]
    resistances = sorted({r for r in resistances if r > last})[:3]
    return supports, resistances


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def compute_technicals(history: PriceHistory) -> TechnicalFeatures:
    """Compute the full technical feature bundle from a price history."""
    tf = TechnicalFeatures()
    closes = history.closes
    if not closes:
        return tf

    last = closes[-1]
    tf.sma20 = sma(closes, 20)
    tf.sma50 = sma(closes, 50)
    tf.sma200 = sma(closes, 200)
    tf.vwap = vwap(history, 20)
    tf.atr = atr(history, 14)
    tf.rsi = rsi(closes, 14)
    tf.rel_volume_20d = relative_volume(history.volumes, 20)
    tf.ret_5d = pct_return(closes, 5)
    tf.ret_20d = pct_return(closes, 20)
    tf.ret_90d = pct_return(closes, 90)

    win = closes[-252:] if len(closes) >= 60 else closes
    hi_52 = max(win)
    lo_52 = min(win)
    tf.dist_52w_high = (last - hi_52) / hi_52 * 100.0 if hi_52 else None
    tf.dist_52w_low = (last - lo_52) / lo_52 * 100.0 if lo_52 else None

    if len(closes) >= 2 and closes[-2]:
        tf.gap_pct = (history.bars[-1].open - closes[-2]) / closes[-2] * 100.0

    tf.support_levels, tf.resistance_levels = find_levels(history)

    # --- composite sub-scores (0..100) --------------------------------------
    # Trend: stacked moving averages + price above them.
    trend = 50.0
    if tf.sma20 and tf.sma50 and tf.sma200:
        if last > tf.sma20:
            trend += 12
        if tf.sma20 > tf.sma50:
            trend += 13
        if tf.sma50 > tf.sma200:
            trend += 15
        if last < tf.sma200:
            trend -= 20
    if tf.ret_90d is not None:
        trend += _clamp(tf.ret_90d, -20, 20) * 0.5
    tf.trend_score = round(_clamp(trend), 1)

    # Breakout: proximity to 52w high on expanding volume.
    breakout = 50.0
    if tf.dist_52w_high is not None:
        breakout += _clamp(20 + tf.dist_52w_high, -30, 30)  # near high -> higher
    if tf.rel_volume_20d:
        breakout += _clamp((tf.rel_volume_20d - 1.0) * 25, -15, 25)
    tf.breakout_score = round(_clamp(breakout), 1)

    # Reversal: oversold RSI near support with positive short-term turn.
    reversal = 50.0
    if tf.rsi is not None:
        reversal += (40 - tf.rsi) * 0.8 if tf.rsi < 40 else (40 - tf.rsi) * 0.3
    if tf.ret_5d is not None and tf.ret_20d is not None and tf.ret_20d < 0 < tf.ret_5d:
        reversal += 12
    tf.reversal_score = round(_clamp(reversal), 1)

    # Volatility score: normalized ATR% (higher = more volatile).
    if tf.atr and last:
        atr_pct = tf.atr / last * 100.0
        tf.volatility_score = round(_clamp(atr_pct * 12.5), 1)
    else:
        rets = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1]
        ]
        tf.volatility_score = round(_clamp(pstdev(rets) * 1500), 1) if len(rets) > 2 else 0.0

    return tf
