"""Core domain models for the Opportunity Engine.

These dataclasses form the shared contract between data providers, the feature
layer, the scoring/ranking engine, and the report writers. The core uses only
the standard library so the engine runs (and is fully testable) without any
third-party dependencies.

Research only. Not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

DISCLAIMER = "Research only. Not financial advice."


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    SPECULATIVE = "Speculative"


class CatalystType(str, Enum):
    EARNINGS = "Earnings"
    AI = "AI"
    SEMICONDUCTORS = "Semiconductors"
    DEFENSE = "Defense"
    SPACE = "Space"
    FDA_APPROVAL = "FDA Approval"
    MA = "M&A"
    BUYBACKS = "Buybacks"
    INSIDER_BUYING = "Insider Buying"
    GOVERNMENT_CONTRACTS = "Government Contracts"
    PRODUCT_LAUNCH = "Product Launch"
    IPO_MOMENTUM = "IPO Momentum"
    MACRO = "Macro"
    RATE_CUTS = "Rate Cuts"
    INDEX_INCLUSION = "Index Inclusion"


class DataFlag(str, Enum):
    """Coarse data-quality flags attached to each opportunity / scan."""
    LIVE_DATA = "LIVE_DATA"                        # all populated fields came from a live provider
    MOCK_DATA = "MOCK_DATA"                        # entirely synthetic (mock) data
    PARTIAL_LIVE_DATA = "PARTIAL_LIVE_DATA"        # mix of live + mock fallback
    STALE_DATA = "STALE_DATA"                      # live price data older than the freshness window
    MISSING_ANALYST_TARGETS = "MISSING_ANALYST_TARGETS"  # no live analyst coverage


class UniverseTag(str, Enum):
    WATCHLIST = "Watchlist"
    HIGH_REL_VOLUME = "High Relative Volume"
    MOMENTUM = "Momentum"
    EARNINGS = "Earnings Strength"
    RECENT_IPO = "Recent IPO"
    UPCOMING_IPO = "Upcoming IPO"
    NEWS_ACTIVITY = "Unusual News"
    ANALYST_UPGRADE = "Analyst Upgrade"
    INSTITUTIONAL = "Institutional Accumulation"
    INSIDER_BUYING = "Insider Buying"
    SECTOR_LEADER = "Sector Leader"
    AI_INFRA = "AI Infrastructure"
    SEMICONDUCTOR = "Semiconductor"
    DEFENSE = "Defense"
    BIOTECH = "Biotech Catalyst"
    SPACE = "Space"
    ENERGY_TRANSITION = "Energy Transition"


# --------------------------------------------------------------------------- #
# Price data
# --------------------------------------------------------------------------- #
@dataclass
class PriceBar:
    dt: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PriceHistory:
    ticker: str
    bars: list[PriceBar] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.bars)

    @property
    def closes(self) -> list[float]:
        return [b.close for b in self.bars]

    @property
    def highs(self) -> list[float]:
        return [b.high for b in self.bars]

    @property
    def lows(self) -> list[float]:
        return [b.low for b in self.bars]

    @property
    def volumes(self) -> list[float]:
        return [b.volume for b in self.bars]

    @property
    def last_close(self) -> float:
        return self.bars[-1].close if self.bars else 0.0


# --------------------------------------------------------------------------- #
# Feature bundles
# --------------------------------------------------------------------------- #
@dataclass
class TechnicalFeatures:
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    vwap: Optional[float] = None
    atr: Optional[float] = None
    rsi: Optional[float] = None
    dist_52w_high: Optional[float] = None   # % below 52w high (negative = below)
    dist_52w_low: Optional[float] = None    # % above 52w low
    rel_volume_20d: Optional[float] = None
    ret_5d: Optional[float] = None
    ret_20d: Optional[float] = None
    ret_90d: Optional[float] = None
    gap_pct: Optional[float] = None
    trend_score: float = 0.0
    breakout_score: float = 0.0
    reversal_score: float = 0.0
    volatility_score: float = 0.0
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)


@dataclass
class FundamentalFeatures:
    revenue_growth: Optional[float] = None
    eps_growth: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    fcf_margin: Optional[float] = None
    cash: Optional[float] = None
    debt: Optional[float] = None
    cash_debt_ratio: Optional[float] = None
    roic: Optional[float] = None
    roe: Optional[float] = None
    pe: Optional[float] = None
    ps: Optional[float] = None
    ev_ebitda: Optional[float] = None
    institutional_ownership: Optional[float] = None
    insider_ownership: Optional[float] = None


@dataclass
class EarningsSurprise:
    period: str
    estimate: float
    actual: float

    @property
    def surprise_pct(self) -> float:
        if self.estimate == 0:
            return 0.0
        return (self.actual - self.estimate) / abs(self.estimate) * 100.0


@dataclass
class EarningsFeatures:
    next_earnings_date: Optional[date] = None
    days_until_earnings: Optional[int] = None
    surprises: list[EarningsSurprise] = field(default_factory=list)
    guidance_revision: Optional[float] = None       # % revision, +ve = raised
    post_earnings_drift: Optional[float] = None      # historical % drift


@dataclass
class IPOFeatures:
    ipo_date: Optional[date] = None
    ipo_price: Optional[float] = None
    ipo_range_low: Optional[float] = None
    ipo_range_high: Optional[float] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    revenue_growth: Optional[float] = None
    lockup_expiration: Optional[date] = None
    perf_30d: Optional[float] = None
    perf_90d: Optional[float] = None
    perf_180d: Optional[float] = None
    is_recent: bool = False
    is_upcoming: bool = False


@dataclass
class AnalystTargets:
    target_low: Optional[float] = None
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    num_analysts: int = 0
    recent_revisions: int = 0          # net up/down revisions, +ve = upgrades
    recommendation_trend: dict[str, int] = field(default_factory=dict)


@dataclass
class Catalyst:
    type: CatalystType
    description: str
    confidence: float = 0.5            # 0..1
    timing: str = "Unknown"            # e.g. "1-2 weeks", "Next quarter"
    impact: float = 0.5                # 0..1 expected magnitude
    source: str = ""
    dt: Optional[date] = None


@dataclass
class NewsItem:
    headline: str
    summary: str = ""
    source: str = ""
    url: str = ""
    dt: Optional[date] = None
    sentiment: float = 0.0             # -1..1


@dataclass
class CatalystFeatures:
    news_count: int = 0
    news_velocity: float = 0.0         # articles/day over lookback
    sentiment_score: float = 0.0       # -1..1
    catalyst_score: float = 0.0        # 0..100
    catalyst_confidence: float = 0.0   # 0..1
    catalyst_timing: str = "Unknown"
    catalyst_impact: float = 0.0       # 0..1
    catalysts: list[Catalyst] = field(default_factory=list)
    news: list[NewsItem] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Scoring / planning / risk / thesis
# --------------------------------------------------------------------------- #
@dataclass
class ScoreBreakdown:
    technical_score: float = 0.0
    fundamental_score: float = 0.0
    quality_score: float = 0.0
    catalyst_score: float = 0.0
    earnings_score: float = 0.0
    ipo_score: float = 0.0
    analyst_score: float = 0.0
    risk_score: float = 0.0            # higher = safer
    final_score: float = 0.0          # 0..100
    weights: dict[str, float] = field(default_factory=dict)


@dataclass
class EntryExitPlan:
    current_price: float = 0.0
    aggressive_entry: float = 0.0
    base_entry: float = 0.0
    conservative_entry: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    risk_reward_ratio: float = 0.0
    expected_return_pct: float = 0.0
    max_drawdown_estimate: float = 0.0
    holding_period: str = "Unknown"


@dataclass
class RiskAssessment:
    level: RiskLevel = RiskLevel.MEDIUM
    factors: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class Thesis:
    summary: str = ""
    bull_case: str = ""
    bear_case: str = ""
    base_case: str = ""
    key_catalysts: list[str] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)


@dataclass
class DataProvenance:
    """Records where each field group came from and the resulting data flags.

    Every ``*_source`` is the name of the provider that actually supplied the
    data ("mock" when synthesized / fallen back). ``fallback_used`` is True when
    any live field had to fall back to the mock.
    """
    price_source: str = "mock"
    company_source: str = "mock"
    sector_source: str = "mock"
    fundamentals_source: str = "mock"
    earnings_source: str = "mock"
    ipo_source: str = "mock"
    analyst_targets_source: str = "mock"
    catalyst_source: str = "mock"

    fallback_used: bool = False
    flags: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    fallback_fields: list[str] = field(default_factory=list)
    stale_warnings: list[str] = field(default_factory=list)
    last_price_date: Optional[date] = None

    def has_flag(self, flag) -> bool:
        value = flag.value if isinstance(flag, Enum) else flag
        return value in self.flags


# --------------------------------------------------------------------------- #
# Top-level opportunity record
# --------------------------------------------------------------------------- #
@dataclass
class Opportunity:
    ticker: str
    company: str = ""
    sector: str = ""
    as_of: Optional[date] = None
    rank: int = 0
    current_price: float = 0.0
    tags: list[str] = field(default_factory=list)

    technicals: TechnicalFeatures = field(default_factory=TechnicalFeatures)
    fundamentals: FundamentalFeatures = field(default_factory=FundamentalFeatures)
    earnings: EarningsFeatures = field(default_factory=EarningsFeatures)
    ipo: IPOFeatures = field(default_factory=IPOFeatures)
    analyst: AnalystTargets = field(default_factory=AnalystTargets)
    catalyst: CatalystFeatures = field(default_factory=CatalystFeatures)

    scores: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    plan: EntryExitPlan = field(default_factory=EntryExitPlan)
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    thesis: Thesis = field(default_factory=Thesis)
    provenance: DataProvenance = field(default_factory=DataProvenance)

    disclaimer: str = DISCLAIMER

    @property
    def expected_upside_pct(self) -> float:
        if self.current_price <= 0 or not self.analyst.target_mean:
            return self.plan.expected_return_pct
        return (self.analyst.target_mean - self.current_price) / self.current_price * 100.0

    @property
    def max_return_pct(self) -> float:
        """Maximum modelled return: upside to the highest target (T3)."""
        if self.current_price <= 0 or self.plan.target_3 <= 0:
            return self.plan.expected_return_pct
        return (self.plan.target_3 - self.current_price) / self.current_price * 100.0

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(self)


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #
def _to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / enums / dates to JSON-safe values."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj
