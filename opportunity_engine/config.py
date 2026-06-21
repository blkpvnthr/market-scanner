"""Configuration system.

Loads settings from environment variables (optionally via a .env file) and
exposes a typed `Settings` object. Every provider is optional: when an API key
is absent the engine falls back to the deterministic mock provider so it always
runs end to end.

Research only. Not financial advice.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _load_dotenv(path: Optional[str] = None) -> None:
    """Best-effort .env loader. Uses python-dotenv if available, else a tiny
    parser. Never raises; missing files are ignored."""
    candidate = Path(path) if path else Path.cwd() / ".env"
    try:  # prefer the real library when installed
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(candidate if candidate.exists() else None)
        return
    except Exception:
        pass
    if not candidate.exists():
        return
    try:
        for line in candidate.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception:
        pass


# Default thematic universe used when no watchlist is configured.
DEFAULT_WATCHLIST = [
    "NVDA", "AMD", "AVGO", "ASML", "TSM", "MU", "ALAB", "MRVL",  # AI / semis
    "PLTR", "MSFT", "GOOGL", "AMZN", "META",                       # AI infra / mega
    "LMT", "RTX", "NOC", "LHX",                                    # defense
    "RKLB", "LUNR", "ASTS",                                        # space
    "LLY", "VRTX", "CRSP",                                         # biotech
    "FSLR", "ENPH", "TSLA",                                        # energy transition
]

# Component weights for the final score (sum need not be 1; normalized later).
DEFAULT_WEIGHTS = {
    "technical": 0.20,
    "fundamental": 0.18,
    "quality": 0.12,
    "catalyst": 0.18,
    "earnings": 0.08,
    "ipo": 0.04,
    "analyst": 0.12,
    "risk": 0.08,
}


@dataclass
class Settings:
    # provider keys (optional)
    alpaca_key: Optional[str] = None
    alpaca_secret: Optional[str] = None
    alpaca_base_url: Optional[str] = None
    alpaca_data_feed: str = "iex"
    finnhub_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None

    # provider selection: "auto" | "mock" | "alpaca" | "finnhub" | "yahoo" | "alpha_vantage"
    provider: str = "auto"

    # universe / scan parameters
    watchlist: list[str] = field(default_factory=lambda: list(DEFAULT_WATCHLIST))
    max_universe: int = 60
    top_n: int = 15
    history_days: int = 260

    # scoring
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    # output
    output_dir: str = "reports_out"
    cache_dir: str = ".cache"

    # email delivery (all optional; engine degrades gracefully without them)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_starttls: bool = True
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    email_top_n: int = 25          # emailed report size (clamped to >=20)

    # reproducibility for the mock provider
    seed: int = 7

    @property
    def has_email(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password
                    and self.email_from and self.email_to)

    @property
    def has_alpaca(self) -> bool:
        return bool(self.alpaca_key and self.alpaca_secret)

    @property
    def has_finnhub(self) -> bool:
        return bool(self.finnhub_key)

    @property
    def has_alpha_vantage(self) -> bool:
        return bool(self.alpha_vantage_key)


def _parse_watchlist(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    items = [t.strip().upper() for t in raw.replace("\n", ",").split(",")]
    return [t for t in items if t] or None


def load_settings(dotenv_path: Optional[str] = None) -> Settings:
    """Build a Settings object from the environment."""
    _load_dotenv(dotenv_path)

    s = Settings(
        alpaca_key=os.getenv("APCA_API_KEY"),
        alpaca_secret=os.getenv("APCA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY"),
        alpaca_base_url=os.getenv("APCA_API_BASE_URL"),
        alpaca_data_feed=os.getenv("ALPACA_DATA_FEED", "iex") or "iex",
        finnhub_key=os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_API"),
        alpha_vantage_key=os.getenv("ALPHA_VANTAGE_API_KEY"),
        provider=os.getenv("OE_PROVIDER", "auto"),
    )

    # email / SMTP (optional)
    s.smtp_host = os.getenv("SMTP_HOST")
    s.smtp_user = os.getenv("SMTP_USER")
    s.smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")
    s.email_from = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER")
    s.email_to = os.getenv("EMAIL_TO")
    if os.getenv("SMTP_PORT"):
        try:
            s.smtp_port = int(os.environ["SMTP_PORT"])
        except ValueError:
            pass
    if os.getenv("SMTP_STARTTLS"):
        s.smtp_starttls = os.environ["SMTP_STARTTLS"].lower() not in {"0", "false", "no"}
    if os.getenv("EMAIL_TOP_N"):
        try:
            s.email_top_n = int(os.environ["EMAIL_TOP_N"])
        except ValueError:
            pass

    wl = _parse_watchlist(os.getenv("OE_WATCHLIST") or os.getenv("BUFFETT_WATCHLIST"))
    if wl:
        s.watchlist = wl

    if os.getenv("OE_TOP_N"):
        try:
            s.top_n = int(os.getenv("OE_TOP_N", "15"))
        except ValueError:
            pass
    if os.getenv("OE_OUTPUT_DIR"):
        s.output_dir = os.environ["OE_OUTPUT_DIR"]
    if os.getenv("OE_SEED"):
        try:
            s.seed = int(os.environ["OE_SEED"])
        except ValueError:
            pass

    return s
