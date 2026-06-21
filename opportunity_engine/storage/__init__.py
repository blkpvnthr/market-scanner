"""Storage: caching and historical persistence. Research only. Not financial advice."""

from .cache import Cache, save_scan_history

__all__ = ["Cache", "save_scan_history"]
