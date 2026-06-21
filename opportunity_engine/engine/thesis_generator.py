"""Thesis generator.

Produces a human-readable investment thesis (summary + bull / bear / base cases)
and distilled catalyst/risk bullet lists from the structured features. The
generation is deterministic and fully driven by the underlying data so every
sentence is traceable to a computed value.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import (
    AnalystTargets,
    CatalystFeatures,
    EntryExitPlan,
    FundamentalFeatures,
    RiskAssessment,
    ScoreBreakdown,
    Thesis,
)


def _growth_phrase(f: FundamentalFeatures) -> str:
    rg = f.revenue_growth
    if rg is None:
        return "a stable revenue base"
    if rg >= 35:
        return f"rapid revenue growth (~{rg:.0f}% YoY)"
    if rg >= 15:
        return f"solid revenue growth (~{rg:.0f}% YoY)"
    if rg >= 0:
        return f"modest revenue growth (~{rg:.0f}% YoY)"
    return f"declining revenue (~{rg:.0f}% YoY)"


def _quality_phrase(scores: ScoreBreakdown) -> str:
    q = scores.quality_score
    if q >= 70:
        return "high-quality margins and returns on capital"
    if q >= 50:
        return "respectable profitability"
    return "thin or improving profitability"


def generate_thesis(
    *,
    ticker: str,
    company: str,
    sector: str,
    fundamentals: FundamentalFeatures,
    catalyst: CatalystFeatures,
    analyst: AnalystTargets,
    scores: ScoreBreakdown,
    risk: RiskAssessment,
    plan: EntryExitPlan,
) -> Thesis:
    name = company or ticker

    # Key catalysts (descriptions of the strongest few).
    key_catalysts = [c.description for c in catalyst.catalysts[:4]] or [
        "Upcoming quarterly earnings report"
    ]

    # Key risks (high-rated factors first, then notes).
    high_factors = [k.replace("_", " ") for k, v in risk.factors.items() if v == "High"]
    key_risks = ([f"Elevated {f} risk" for f in high_factors] + risk.notes)[:4]
    if not key_risks:
        key_risks = ["General market and execution risk"]

    upside = ""
    if analyst.target_mean and plan.current_price:
        up = (analyst.target_mean - plan.current_price) / plan.current_price * 100
        upside = (f" Consensus analyst targets imply ~{up:.0f}% upside "
                  f"(mean ${analyst.target_mean:,.0f} across {analyst.num_analysts} analysts).")

    summary = (
        f"{name} ({ticker}) is a {sector.lower()} name backed by {_growth_phrase(fundamentals)} "
        f"and {_quality_phrase(scores)}. The setup is supported by {key_catalysts[0].lower()}"
        f"{' and ' + key_catalysts[1].lower() if len(key_catalysts) > 1 else ''}."
        f"{upside} Composite opportunity score: {scores.final_score:.0f}/100. "
        f"Primary risks include {key_risks[0].lower()}."
    )

    bull = (
        f"Bull case: continued execution on {key_catalysts[0].lower()} re-rates {ticker} toward "
        f"the upper analyst target (${analyst.target_high:,.0f})."
        if analyst.target_high else
        f"Bull case: continued execution on {key_catalysts[0].lower()} drives multiple expansion "
        f"and a move toward target {plan.target_3:,.0f}."
    ) + f" Trend score {scores.technical_score:.0f} and catalyst score {scores.catalyst_score:.0f} support momentum."

    bear = (
        f"Bear case: {key_risks[0].lower()} pressures the multiple; failure to hold "
        f"${plan.stop_loss:,.0f} (stop) would invalidate the thesis, with downside toward the "
        f"conservative entry near ${plan.conservative_entry:,.0f}."
    )

    base = (
        f"Base case: {ticker} grinds higher with the sector, reaching target ${plan.target_2:,.0f} "
        f"(~{plan.expected_return_pct:.0f}% from spot) over a {plan.holding_period} horizon "
        f"at a {plan.risk_reward_ratio:.1f}:1 reward/risk. Risk level: {risk.level.value}."
    )

    return Thesis(
        summary=summary,
        bull_case=bull,
        bear_case=bear,
        base_case=base,
        key_catalysts=key_catalysts,
        key_risks=key_risks,
    )
