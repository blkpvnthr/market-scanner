"""Per-opportunity formatting.

Renders a single :class:`Opportunity` into the detailed Markdown block described
in the output spec (entry zones, targets, analyst targets, catalysts, thesis,
risks and the full score breakdown).

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import Opportunity


def _money(x: float) -> str:
    return f"${x:,.2f}" if abs(x) < 1000 else f"${x:,.0f}"


def format_opportunity_md(opp: Opportunity) -> str:
    s = opp.scores
    p = opp.plan
    a = opp.analyst
    lines: list[str] = []
    lines.append(f"## #{opp.rank} {opp.ticker} — {opp.company}")
    lines.append(f"*{opp.sector} · Score {s.final_score:.0f}/100 · Risk {opp.risk.level.value}*")
    if opp.tags:
        lines.append(f"`{'` `'.join(opp.tags)}`")
    prov = opp.provenance
    flag_str = " ".join(f"`{f}`" for f in prov.flags) if prov.flags else "`MOCK_DATA`"
    lines.append(
        f"**Data:** {flag_str} · price={prov.price_source}, "
        f"analyst={prov.analyst_targets_source}, catalyst={prov.catalyst_source}"
        + (f" · ⚠ {prov.stale_warnings[0]}" if prov.stale_warnings else "")
    )
    lines.append("")
    lines.append(f"**Current Price:** {_money(opp.current_price)}")
    lines.append("")
    lines.append("**Entry Zones**")
    lines.append(f"- Aggressive (breakout): {_money(p.aggressive_entry)}")
    lines.append(f"- Base (support retest): {_money(p.base_entry)}")
    lines.append(f"- Conservative (pullback): {_money(p.conservative_entry)}")
    lines.append(f"- **Stop Loss:** {_money(p.stop_loss)}")
    lines.append("")
    lines.append("**Targets**")
    lines.append(f"- T1 (1R): {_money(p.target_1)}")
    lines.append(f"- T2 (resistance / measured move): {_money(p.target_2)}")
    lines.append(f"- T3 (analyst / trend): {_money(p.target_3)}")
    lines.append("")
    if a.target_mean:
        lines.append(
            f"**Analyst Targets:** Low {_money(a.target_low or 0)} · "
            f"Mean {_money(a.target_mean)} · High {_money(a.target_high or 0)} "
            f"({a.num_analysts} analysts)"
        )
    lines.append(
        f"**Expected Upside:** {opp.expected_upside_pct:.1f}% · "
        f"**R/R:** {p.risk_reward_ratio:.1f}:1 · "
        f"**Max DD est:** {p.max_drawdown_estimate:.1f}% · "
        f"**Hold:** {p.holding_period}"
    )
    lines.append("")
    lines.append(
        f"**Catalysts** (confidence {opp.catalyst.catalyst_confidence:.0%}, "
        f"timing {opp.catalyst.catalyst_timing}, "
        f"score {opp.catalyst.catalyst_score:.0f}):"
    )
    for c in opp.catalyst.catalysts[:5]:
        lines.append(f"- [{c.type.value}] {c.description} ({c.confidence:.0%})")
    lines.append("")
    lines.append(f"**Thesis:** {opp.thesis.summary}")
    lines.append("")
    lines.append(f"**Bull:** {opp.thesis.bull_case}")
    lines.append(f"**Bear:** {opp.thesis.bear_case}")
    lines.append(f"**Base:** {opp.thesis.base_case}")
    lines.append("")
    lines.append("**Key Risks:** " + "; ".join(opp.thesis.key_risks))
    lines.append("")
    lines.append(
        "**Score Breakdown:** "
        f"Tech {s.technical_score:.0f} · "
        f"Fund {s.fundamental_score:.0f} · "
        f"Quality {s.quality_score:.0f} · "
        f"Catalyst {s.catalyst_score:.0f} · "
        f"Earnings {s.earnings_score:.0f} · "
        f"IPO {s.ipo_score:.0f} · "
        f"Analyst {s.analyst_score:.0f} · "
        f"Risk(safety) {s.risk_score:.0f} → **Final {s.final_score:.0f}**"
    )
    lines.append("")
    lines.append("---")
    return "\n".join(lines)
