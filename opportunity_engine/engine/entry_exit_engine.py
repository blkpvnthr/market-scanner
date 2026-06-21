"""Entry / exit engine.

Derives three entry zones (aggressive breakout, base support-retest,
conservative deep-pullback), an ATR/support-based stop, and three layered
targets (1R, prior-resistance / measured-move, analyst / trend projection) from
the price, technicals and analyst targets. Also returns risk/reward, expected
return and an estimated max drawdown.

Research only. Not financial advice.
"""

from __future__ import annotations

from ..models import AnalystTargets, EntryExitPlan, TechnicalFeatures


def _nearest_below(levels: list[float], price: float) -> float | None:
    below = [l for l in levels if l < price]
    return max(below) if below else None


def _nearest_above(levels: list[float], price: float) -> float | None:
    above = [l for l in levels if l > price]
    return min(above) if above else None


def build_plan(
    current_price: float,
    technicals: TechnicalFeatures,
    analyst: AnalystTargets,
) -> EntryExitPlan:
    price = current_price
    if price <= 0:
        return EntryExitPlan(current_price=0.0, holding_period="Unknown")

    atr = technicals.atr or price * 0.02
    sma20 = technicals.sma20 or price
    sma50 = technicals.sma50 or price * 0.95
    support = _nearest_below(technicals.support_levels, price)
    resistance = _nearest_above(technicals.resistance_levels, price)

    # --- entries ------------------------------------------------------------
    aggressive = round(price + 0.25 * atr, 2)                       # breakout continuation
    base = round(min(price - 0.6 * atr, support or sma20), 2)       # support retest
    base = min(base, price - 0.2 * atr)                            # never above market
    conservative = round(min(base - 1.2 * atr, sma50), 2)          # deep pullback zone

    # --- stop ---------------------------------------------------------------
    atr_stop = conservative - 1.0 * atr
    support_stop = (support * 0.97) if support else atr_stop
    stop = round(min(atr_stop, support_stop), 2)
    stop = min(stop, conservative - 0.1 * atr)                    # ensure below entries

    # --- targets ------------------------------------------------------------
    r = base - stop                                                # 1R risk unit
    target_1 = round(base + r, 2)                                  # 1R
    measured = base + 2.2 * r
    target_2 = round(max(resistance or 0, measured), 2)           # prior resistance / measured move
    analyst_t = analyst.target_mean or analyst.target_high
    trend_proj = base + 3.5 * r
    target_3 = round(max(analyst_t or 0, trend_proj, target_2 * 1.05), 2)

    # Keep monotonically increasing.
    target_2 = max(target_2, target_1 + 0.01)
    target_3 = max(target_3, target_2 + 0.01)

    # --- metrics ------------------------------------------------------------
    reward = target_2 - base
    risk = max(base - stop, 0.01)
    rr = round(reward / risk, 2)
    expected_return = round((target_2 - price) / price * 100, 1)
    max_dd = round((stop - price) / price * 100, 1)

    # --- holding period -----------------------------------------------------
    if technicals.trend_score >= 65 and technicals.breakout_score >= 60:
        holding = "3-9 months (trend follow)"
    elif technicals.reversal_score >= 60:
        holding = "1-3 months (mean reversion)"
    else:
        holding = "3-6 months (swing/position)"

    return EntryExitPlan(
        current_price=round(price, 2),
        aggressive_entry=aggressive,
        base_entry=base,
        conservative_entry=conservative,
        stop_loss=stop,
        target_1=target_1,
        target_2=round(target_2, 2),
        target_3=round(target_3, 2),
        risk_reward_ratio=rr,
        expected_return_pct=expected_return,
        max_drawdown_estimate=max_dd,
        holding_period=holding,
    )
