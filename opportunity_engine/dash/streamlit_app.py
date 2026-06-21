"""Streamlit dashboard for the Opportunity Engine (Phase 3).

Run with:  python -m opportunity_engine dashboard
       or:  streamlit run opportunity_engine/dash/streamlit_app.py

Renders the ranked watchlist, an interactive detail view, and the model
portfolios. Requires ``streamlit`` (optional dependency).

Research only. Not financial advice.
"""

from __future__ import annotations


def main() -> None:
    import streamlit as st

    from opportunity_engine.config import load_settings
    from opportunity_engine.engine import run_scan
    from opportunity_engine.engine.opportunity_report import format_opportunity_md
    from opportunity_engine.models import DISCLAIMER
    from opportunity_engine.portfolio import build_portfolios

    st.set_page_config(page_title="Opportunity Engine", layout="wide")
    st.title("📈 Opportunity Engine — Daily Research Watchlist")
    st.caption(DISCLAIMER)

    settings = load_settings()
    with st.sidebar:
        st.header("Settings")
        settings.provider = st.selectbox(
            "Provider", ["mock", "auto", "yahoo", "alpaca", "finnhub", "alpha_vantage"], index=0
        )
        settings.top_n = st.slider("Top N", 5, 40, settings.top_n)

    @st.cache_data(show_spinner=True)
    def _scan(provider: str, top_n: int, seed: int):
        settings.provider = provider
        settings.top_n = top_n
        return run_scan(settings)

    result = _scan(settings.provider, settings.top_n, settings.seed)
    st.success(f"Scanned {len(result.opportunities)} names · provider: {result.provider} · {result.as_of}")

    rows = [
        {
            "Rank": o.rank, "Ticker": o.ticker, "Company": o.company,
            "Sector": o.sector, "Price": o.current_price, "Score": o.scores.final_score,
            "Risk": o.risk.level.value, "Upside %": round(o.expected_upside_pct, 1),
            "R/R": o.plan.risk_reward_ratio,
            "Catalyst": o.catalyst.catalysts[0].description if o.catalyst.catalysts else "-",
        }
        for o in result.top
    ]
    st.subheader("Ranked Watchlist")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Opportunity Detail")
    tickers = [o.ticker for o in result.top]
    if tickers:
        choice = st.selectbox("Select a ticker", tickers)
        opp = next(o for o in result.top if o.ticker == choice)
        st.markdown(format_opportunity_md(opp))

    st.subheader("Model Portfolios")
    ports = build_portfolios(result.opportunities)
    cols = st.columns(len(ports))
    for col, (key, port) in zip(cols, ports.items()):
        with col:
            st.metric(port.name, f"{port.expected_return_pct:.0f}%",
                      f"Sharpe {port.sharpe:.2f}")
            st.caption(f"Vol {port.expected_volatility_pct:.0f}% · DD {port.expected_drawdown_pct:.0f}%")
            st.dataframe(
                [{"Ticker": p.ticker, "Wt %": round(p.weight * 100, 1)} for p in port.positions],
                hide_index=True,
            )

    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
