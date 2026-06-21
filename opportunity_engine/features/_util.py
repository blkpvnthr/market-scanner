"""Small shared scoring helpers. Research only. Not financial advice."""

from __future__ import annotations

from typing import Optional


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def scale(value: Optional[float], lo: float, hi: float) -> float:
    """Linearly map ``value`` in [lo, hi] to [0, 100], clamped. None -> 50."""
    if value is None:
        return 50.0
    if hi == lo:
        return 50.0
    return clamp((value - lo) / (hi - lo) * 100.0)
