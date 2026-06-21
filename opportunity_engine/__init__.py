"""Opportunity Engine — a research-first investment opportunity scanner.

Discovers, scores, ranks and explains investment opportunities across growth,
value, quality, IPOs, earnings, news and catalyst-driven setups. Research only:
it never places orders and requires no broker credentials.

Research only. Not financial advice.
"""

from __future__ import annotations

from .config import Settings, load_settings
from .engine import run_scan, ScanResult
from .models import DISCLAIMER, Opportunity

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "load_settings",
    "run_scan",
    "ScanResult",
    "Opportunity",
    "DISCLAIMER",
    "__version__",
]
