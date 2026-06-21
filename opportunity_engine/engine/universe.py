"""Universe generation.

Builds the daily candidate universe from the configured watchlist plus thematic
buckets (AI infra, semis, defense, space, biotech, energy transition) and the
recent / upcoming IPO sets. Each ticker carries a set of descriptive tags that
explain *why* it is in the universe; these tags surface later in the report.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..models import UniverseTag

# Thematic seed buckets. These mirror the universe-generation spec and give the
# engine a research-driven starting set even with no live screening.
THEMES: dict[UniverseTag, list[str]] = {
    UniverseTag.AI_INFRA: ["NVDA", "AVGO", "ALAB", "PLTR", "MSFT", "AMZN", "GOOGL", "META", "APLD"],
    UniverseTag.SEMICONDUCTOR: ["NVDA", "AMD", "AVGO", "ASML", "TSM", "MU", "MRVL", "QCOM", "AMAT"],
    UniverseTag.DEFENSE: ["LMT", "RTX", "NOC", "LHX"],
    UniverseTag.SPACE: ["RKLB", "LUNR", "ASTS"],
    UniverseTag.BIOTECH: ["LLY", "VRTX", "CRSP", "IDYA"],
    UniverseTag.ENERGY_TRANSITION: ["FSLR", "ENPH", "TSLA", "SUNE"],
}

RECENT_IPOS = ["ALAB", "RKLB", "LUNR", "ASTS"]
UPCOMING_IPOS = ["STRIPE", "CHIME", "DATABRICKS"]


@dataclass
class UniverseEntry:
    ticker: str
    tags: set[UniverseTag] = field(default_factory=set)

    @property
    def tag_labels(self) -> list[str]:
        return sorted(t.value for t in self.tags)


def build_universe(settings: Settings) -> list[UniverseEntry]:
    entries: dict[str, UniverseEntry] = {}

    def add(ticker: str, tag: UniverseTag) -> None:
        ticker = ticker.upper()
        entries.setdefault(ticker, UniverseEntry(ticker)).tags.add(tag)

    for t in settings.watchlist:
        add(t, UniverseTag.WATCHLIST)

    for tag, tickers in THEMES.items():
        for t in tickers:
            add(t, tag)

    for t in RECENT_IPOS:
        add(t, UniverseTag.RECENT_IPO)
    for t in UPCOMING_IPOS:
        add(t, UniverseTag.UPCOMING_IPO)

    # Deterministic ordering: watchlist names first, then the rest alphabetically.
    watch = [e for e in entries.values() if UniverseTag.WATCHLIST in e.tags]
    rest = [e for e in entries.values() if UniverseTag.WATCHLIST not in e.tags]
    ordered = sorted(watch, key=lambda e: e.ticker) + sorted(rest, key=lambda e: e.ticker)
    return ordered[: settings.max_universe]
