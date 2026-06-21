"""Deterministic mock data provider.

Generates realistic, reproducible synthetic data for any ticker, seeded by the
ticker symbol so results are stable across runs. Price histories are real OHLCV
series (with trend + volatility regimes) so the technical layer computes genuine
indicators; fundamentals, earnings, IPO, analyst and catalyst data are plausible
values drawn from seeded distributions.

This is the Phase-1 default provider and the universal fallback.

Research only. Not financial advice.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from ..models import (
    AnalystTargets,
    Catalyst,
    CatalystFeatures,
    CatalystType,
    EarningsFeatures,
    EarningsSurprise,
    FundamentalFeatures,
    IPOFeatures,
    NewsItem,
    PriceBar,
    PriceHistory,
)
from .base import DataProvider

# Thematic metadata used to colour the synthetic data with sector logic.
SECTOR_MAP: dict[str, str] = {
    "NVDA": "Semiconductors", "AMD": "Semiconductors", "AVGO": "Semiconductors",
    "ASML": "Semiconductors", "TSM": "Semiconductors", "MU": "Semiconductors",
    "ALAB": "Semiconductors", "MRVL": "Semiconductors", "INTC": "Semiconductors",
    "QCOM": "Semiconductors", "AMAT": "Semiconductors", "SMCI": "Technology",
    "PLTR": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Technology", "META": "Technology", "APLD": "Technology",
    "LMT": "Defense", "RTX": "Defense", "NOC": "Defense", "LHX": "Defense",
    "RKLB": "Aerospace", "LUNR": "Aerospace", "ASTS": "Aerospace",
    "LLY": "Biotech", "VRTX": "Biotech", "CRSP": "Biotech", "IDYA": "Biotech",
    "FSLR": "Energy", "ENPH": "Energy", "TSLA": "Autos", "SUNE": "Energy",
    "IONQ": "Quantum", "QBTS": "Quantum", "RGTI": "Quantum",
}

COMPANY_NAMES: dict[str, str] = {
    "NVDA": "NVIDIA Corporation", "AMD": "Advanced Micro Devices",
    "AVGO": "Broadcom Inc.", "ASML": "ASML Holding N.V.",
    "TSM": "Taiwan Semiconductor", "MU": "Micron Technology",
    "ALAB": "Astera Labs", "MRVL": "Marvell Technology",
    "PLTR": "Palantir Technologies", "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.", "AMZN": "Amazon.com Inc.", "META": "Meta Platforms",
    "LMT": "Lockheed Martin", "RTX": "RTX Corporation", "NOC": "Northrop Grumman",
    "LHX": "L3Harris Technologies", "RKLB": "Rocket Lab USA", "LUNR": "Intuitive Machines",
    "ASTS": "AST SpaceMobile", "LLY": "Eli Lilly", "VRTX": "Vertex Pharmaceuticals",
    "CRSP": "CRISPR Therapeutics", "FSLR": "First Solar", "ENPH": "Enphase Energy",
    "TSLA": "Tesla Inc.",
}

# Tickers treated as recent or upcoming IPOs in the mock world.
RECENT_IPOS = {"ALAB", "RKLB", "LUNR", "ASTS", "RDDT", "ARM"}
UPCOMING_IPOS = {"STRIPE", "DBX2", "CHIME", "SHEIN", "DATABRICKS"}

# Base prices to make output look familiar.
BASE_PRICES: dict[str, float] = {
    "NVDA": 135, "AMD": 165, "AVGO": 175, "ASML": 980, "TSM": 185, "MU": 110,
    "ALAB": 95, "MRVL": 78, "PLTR": 42, "MSFT": 440, "GOOGL": 180, "AMZN": 195,
    "META": 580, "LMT": 470, "RTX": 120, "NOC": 480, "LHX": 240, "RKLB": 24,
    "LUNR": 11, "ASTS": 28, "LLY": 880, "VRTX": 470, "CRSP": 55, "FSLR": 220,
    "ENPH": 95, "TSLA": 250,
}


def _seed(ticker: str, salt: int = 0) -> random.Random:
    return random.Random(f"{ticker}:{salt}")


class MockProvider(DataProvider):
    name = "mock"

    def __init__(self, seed: int = 7):
        self.seed = seed
        self._close_cache: dict[str, float] = {}

    def available(self) -> bool:
        return True

    def _last_close(self, ticker: str) -> float:
        """Deterministic spot price = last close of the generated series.

        Cached so analyst targets / IPO performance stay coherent with the
        price history without regenerating it each time.
        """
        if ticker not in self._close_cache:
            self._close_cache[ticker] = self.get_price_history(ticker, 260).last_close
        return self._close_cache[ticker]

    # ----------------------------------------------------------------- prices
    def get_price_history(self, ticker: str, days: int = 260) -> PriceHistory:
        rng = _seed(ticker, self.seed)
        start_price = BASE_PRICES.get(ticker, rng.uniform(15, 400))

        # Per-ticker regime: drift and volatility.
        drift = rng.uniform(-0.0006, 0.0018)          # daily mean return
        vol = rng.uniform(0.012, 0.045)               # daily stdev
        # Inject a mild momentum bias for momentum/AI names.
        if SECTOR_MAP.get(ticker) in {"Semiconductors", "Technology"}:
            drift += 0.0005

        bars: list[PriceBar] = []
        price = start_price * rng.uniform(0.6, 0.9)   # start below current
        today = date(2026, 6, 19)
        start_day = today - timedelta(days=int(days * 1.45))
        d = start_day
        count = 0
        while count < days:
            if d.weekday() < 5:  # trading days only
                ret = rng.gauss(drift, vol)
                open_ = price
                close = max(0.5, price * (1 + ret))
                high = max(open_, close) * (1 + abs(rng.gauss(0, vol / 2)))
                low = min(open_, close) * (1 - abs(rng.gauss(0, vol / 2)))
                base_vol = rng.uniform(2e6, 5e7)
                volume = base_vol * (1 + abs(ret) * 8)  # volume expands on moves
                bars.append(PriceBar(d, round(open_, 2), round(high, 2),
                                     round(low, 2), round(close, 2), round(volume)))
                price = close
                count += 1
            d += timedelta(days=1)
        return PriceHistory(ticker, bars)

    def get_company_name(self, ticker: str) -> str:
        return COMPANY_NAMES.get(ticker, f"{ticker} Inc.")

    def get_sector(self, ticker: str) -> str:
        return SECTOR_MAP.get(ticker, "Diversified")

    # ----------------------------------------------------------- fundamentals
    def get_fundamentals(self, ticker: str) -> FundamentalFeatures:
        rng = _seed(ticker, self.seed + 1)
        sector = self.get_sector(ticker)
        growthy = sector in {"Semiconductors", "Technology", "Biotech", "Quantum", "Aerospace"}

        rev_growth = rng.uniform(0.18, 0.65) if growthy else rng.uniform(-0.05, 0.18)
        gross = rng.uniform(0.45, 0.78) if growthy else rng.uniform(0.25, 0.5)
        op = gross - rng.uniform(0.1, 0.35)
        cash = rng.uniform(1e9, 6e10)
        debt = rng.uniform(0, 4e10)
        return FundamentalFeatures(
            revenue_growth=round(rev_growth * 100, 1),
            eps_growth=round(rng.uniform(-0.1, 0.9) * 100, 1),
            gross_margin=round(gross * 100, 1),
            operating_margin=round(op * 100, 1),
            fcf_margin=round(max(-0.1, op - rng.uniform(0, 0.1)) * 100, 1),
            cash=round(cash),
            debt=round(debt),
            cash_debt_ratio=round(cash / debt, 2) if debt else 99.0,
            roic=round(rng.uniform(2, 35), 1),
            roe=round(rng.uniform(5, 45), 1),
            pe=round(rng.uniform(12, 80), 1),
            ps=round(rng.uniform(2, 30), 1),
            ev_ebitda=round(rng.uniform(8, 45), 1),
            institutional_ownership=round(rng.uniform(40, 92), 1),
            insider_ownership=round(rng.uniform(0.5, 18), 1),
        )

    # ---------------------------------------------------------------- earnings
    def get_earnings(self, ticker: str) -> EarningsFeatures:
        rng = _seed(ticker, self.seed + 2)
        days_until = rng.randint(2, 75)
        next_date = date(2026, 6, 19) + timedelta(days=days_until)
        surprises = []
        for q in range(4):
            est = rng.uniform(0.5, 4.0)
            actual = est * (1 + rng.uniform(-0.08, 0.18))
            surprises.append(EarningsSurprise(f"Q{4 - q}", round(est, 2), round(actual, 2)))
        return EarningsFeatures(
            next_earnings_date=next_date,
            days_until_earnings=days_until,
            surprises=surprises,
            guidance_revision=round(rng.uniform(-5, 12), 1),
            post_earnings_drift=round(rng.uniform(-4, 9), 1),
        )

    # -------------------------------------------------------------------- IPO
    def get_ipo(self, ticker: str) -> IPOFeatures:
        rng = _seed(ticker, self.seed + 3)
        recent = ticker in RECENT_IPOS
        upcoming = ticker in UPCOMING_IPOS
        if not (recent or upcoming):
            return IPOFeatures(sector=self.get_sector(ticker))
        ipo_price = BASE_PRICES.get(ticker, rng.uniform(15, 60)) * rng.uniform(0.6, 0.95)
        feats = IPOFeatures(
            ipo_price=round(ipo_price, 2),
            ipo_range_low=round(ipo_price * 0.9, 2),
            ipo_range_high=round(ipo_price * 1.1, 2),
            market_cap=round(rng.uniform(2e9, 4e10)),
            sector=self.get_sector(ticker),
            revenue_growth=round(rng.uniform(30, 120), 1),
            is_recent=recent,
            is_upcoming=upcoming,
        )
        if recent:
            feats.ipo_date = date(2026, 6, 19) - timedelta(days=rng.randint(20, 160))
            feats.lockup_expiration = feats.ipo_date + timedelta(days=180)
            feats.perf_30d = round(rng.uniform(-25, 60), 1)
            feats.perf_90d = round(rng.uniform(-35, 110), 1)
            feats.perf_180d = round(rng.uniform(-40, 180), 1)
        if upcoming:
            feats.ipo_date = date(2026, 6, 19) + timedelta(days=rng.randint(7, 90))
        return feats

    # ----------------------------------------------------------- analyst data
    def get_analyst_targets(self, ticker: str) -> AnalystTargets:
        rng = _seed(ticker, self.seed + 4)
        price = self._last_close(ticker)  # anchor to actual spot for coherent upside
        mean_upside = rng.uniform(-0.1, 0.45)
        mean_t = price * (1 + mean_upside)
        n = rng.randint(4, 48)
        buys = rng.randint(0, n)
        holds = rng.randint(0, n - buys)
        sells = n - buys - holds
        return AnalystTargets(
            target_low=round(mean_t * rng.uniform(0.7, 0.9), 2),
            target_mean=round(mean_t, 2),
            target_high=round(mean_t * rng.uniform(1.1, 1.4), 2),
            num_analysts=n,
            recent_revisions=rng.randint(-4, 9),
            recommendation_trend={"buy": buys, "hold": holds, "sell": sells},
        )

    # -------------------------------------------------------------- catalysts
    def get_catalysts(self, ticker: str) -> CatalystFeatures:
        rng = _seed(ticker, self.seed + 5)
        sector = self.get_sector(ticker)
        catalysts: list[Catalyst] = []

        sector_catalyst = {
            "Semiconductors": (CatalystType.SEMICONDUCTORS, "Semiconductor capex cycle and AI accelerator demand"),
            "Technology": (CatalystType.AI, "AI infrastructure buildout driving compute demand"),
            "Defense": (CatalystType.DEFENSE, "Elevated defense budgets and new program awards"),
            "Aerospace": (CatalystType.SPACE, "Expanding commercial launch cadence and contract backlog"),
            "Biotech": (CatalystType.FDA_APPROVAL, "Pipeline readouts and potential FDA approval catalysts"),
            "Energy": (CatalystType.MACRO, "Energy transition incentives and capacity expansion"),
            "Quantum": (CatalystType.AI, "Quantum roadmap milestones and enterprise pilots"),
        }.get(sector)
        if sector_catalyst:
            ctype, desc = sector_catalyst
            catalysts.append(Catalyst(ctype, desc, confidence=rng.uniform(0.55, 0.9),
                                      timing=rng.choice(["1-3 months", "Next quarter", "Ongoing"]),
                                      impact=rng.uniform(0.5, 0.9), source="thematic"))

        # Earnings catalyst is near-universal.
        catalysts.append(Catalyst(CatalystType.EARNINGS,
                                  "Upcoming quarterly earnings report",
                                  confidence=rng.uniform(0.5, 0.85),
                                  timing="Within ~1 quarter",
                                  impact=rng.uniform(0.4, 0.8), source="calendar"))

        # Random extra catalysts.
        pool = [
            (CatalystType.GOVERNMENT_CONTRACTS, "New government / agency contract award"),
            (CatalystType.PRODUCT_LAUNCH, "Major product launch on the roadmap"),
            (CatalystType.MA, "M&A / consolidation speculation in the space"),
            (CatalystType.BUYBACKS, "Active share repurchase authorization"),
            (CatalystType.INSIDER_BUYING, "Recent insider buying activity"),
            (CatalystType.INDEX_INCLUSION, "Potential index inclusion candidate"),
            (CatalystType.RATE_CUTS, "Rate-cut tailwind for long-duration growth"),
        ]
        for ctype, desc in rng.sample(pool, k=rng.randint(1, 3)):
            catalysts.append(Catalyst(ctype, desc, confidence=rng.uniform(0.3, 0.7),
                                      timing=rng.choice(["Weeks", "1-3 months", "Ongoing"]),
                                      impact=rng.uniform(0.3, 0.7), source="news"))

        if ticker in RECENT_IPOS:
            catalysts.append(Catalyst(CatalystType.IPO_MOMENTUM,
                                      "Recent IPO momentum and index/analyst initiation",
                                      confidence=rng.uniform(0.5, 0.8), timing="1-3 months",
                                      impact=rng.uniform(0.5, 0.85), source="ipo"))

        news_count = rng.randint(3, 40)
        news = [
            NewsItem(headline=f"{ticker}: {c.description}", summary=c.description,
                     source=c.source or "wire", dt=date(2026, 6, 19) - timedelta(days=rng.randint(0, 6)),
                     sentiment=rng.uniform(-0.2, 0.8))
            for c in catalysts[:5]
        ]
        sentiment = round(sum(n.sentiment for n in news) / len(news), 2) if news else 0.0

        return CatalystFeatures(
            news_count=news_count,
            news_velocity=round(news_count / 7.0, 2),
            sentiment_score=sentiment,
            catalysts=catalysts,
            news=news,
        )
