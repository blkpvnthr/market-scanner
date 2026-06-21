"""Command-line interface.

    python -m opportunity_engine scan        # run a scan, print the watchlist
    python -m opportunity_engine report      # run a scan, write all reports to disk
    python -m opportunity_engine backfill    # snapshot scan scores into SQLite
    python -m opportunity_engine portfolio   # build model portfolios
    python -m opportunity_engine dashboard   # launch the Streamlit dashboard

Research only. Not financial advice.
"""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .engine import run_scan
from .engine.opportunity_report import format_opportunity_md
from .models import DISCLAIMER


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default=None,
                   help="mock | auto | yahoo | alpaca | finnhub | alpha_vantage")
    p.add_argument("--top", type=int, default=None, help="number of opportunities to show")
    p.add_argument("--output", default=None, help="output directory for reports")
    p.add_argument("--tickers", default=None,
                   help="comma-separated tickers to restrict the scan to")
    p.add_argument("--limit", type=int, default=None, help="cap the universe size")


def _settings_from_args(args) -> "object":
    s = load_settings()
    if getattr(args, "provider", None):
        s.provider = args.provider
    if getattr(args, "top", None):
        s.top_n = args.top
    if getattr(args, "output", None):
        s.output_dir = args.output
    if getattr(args, "tickers", None):
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        if tickers:
            s.watchlist = tickers
            s.max_universe = len(tickers)  # watchlist is ordered first -> exactly these
    if getattr(args, "limit", None):
        s.max_universe = args.limit
    return s


def cmd_scan(args) -> int:
    settings = _settings_from_args(args)
    result = run_scan(settings)
    print(f"# Opportunity Scan — {result.as_of} (provider: {result.provider})")
    print(f"> {DISCLAIMER}\n")
    print(f"{'#':>2}  {'Ticker':<7} {'Score':>5}  {'Risk':<11} {'Upside':>7}  {'R/R':>4}  Top catalyst")
    print("-" * 92)
    for o in result.top:
        cat = o.catalyst.catalysts[0].description if o.catalyst.catalysts else "-"
        print(f"{o.rank:>2}  {o.ticker:<7} {o.scores.final_score:>5.0f}  "
              f"{o.risk.level.value:<11} {o.expected_upside_pct:>6.0f}%  "
              f"{o.plan.risk_reward_ratio:>4.1f}  {cat[:42]}")
    print(f"\n{DISCLAIMER}")
    return 0


def cmd_report(args) -> int:
    from .reports import write_all_reports

    settings = _settings_from_args(args)
    result = run_scan(settings)
    written = write_all_reports(result, settings.output_dir)
    print(f"Wrote {len(written)} reports to {settings.output_dir}/ (provider: {result.provider}):")
    for name, path in written.items():
        print(f"  - {path}")
    print(f"\n{DISCLAIMER}")
    return 0


def cmd_detail(args) -> int:
    settings = _settings_from_args(args)
    result = run_scan(settings)
    for o in result.top:
        print(format_opportunity_md(o))
        print()
    print(DISCLAIMER)
    return 0


def cmd_backfill(args) -> int:
    from .storage import save_scan_history

    settings = _settings_from_args(args)
    result = run_scan(settings)
    save_scan_history(result)
    print(f"Backfilled {len(result.opportunities)} rows into storage/sqlite/history.db")
    print(DISCLAIMER)
    return 0


def cmd_portfolio(args) -> int:
    from .portfolio import build_portfolios

    settings = _settings_from_args(args)
    result = run_scan(settings)
    ports = build_portfolios(result.opportunities)
    print(f"# Model Portfolios — {result.as_of}\n> {DISCLAIMER}\n")
    for key, port in ports.items():
        print(f"## {port.name}  "
              f"(exp return {port.expected_return_pct:.0f}%, vol {port.expected_volatility_pct:.0f}%, "
              f"Sharpe {port.sharpe:.2f}, est DD {port.expected_drawdown_pct:.0f}%)")
        for p in port.positions:
            print(f"   {p.ticker:<7} {p.weight*100:>5.1f}%  {p.sector:<14} "
                  f"score {p.final_score:.0f}  upside {p.expected_upside_pct:.0f}%  {p.risk_level}")
        print()
    print(DISCLAIMER)
    return 0


def cmd_email(args) -> int:
    from pathlib import Path

    from .reports.email import render_email_html, send_report_email

    settings = _settings_from_args(args)
    if getattr(args, "to", None):
        settings.email_to = args.to
    # Guarantee the emailed report can hold >=20 ranked candidates.
    settings.email_top_n = max(20, settings.email_top_n)
    if settings.max_universe < 25:
        settings.max_universe = 60

    result = run_scan(settings)

    if getattr(args, "html_out", None):
        Path(args.html_out).write_text(render_email_html(result))
        print(f"Wrote HTML preview to {args.html_out}")

    res = send_report_email(result, settings, dry_run=bool(getattr(args, "dry_run", False)))
    status = "SENT" if res.sent else f"NOT SENT ({res.reason})"
    print(f"[{status}] {res.subject}")
    print(f"  recipient : {res.recipient or '(none)'}")
    print(f"  candidates: {res.candidate_count} (ranked best→worst by max return)")
    if not res.sent and res.reason not in ("dry-run",):
        print("  Tip: set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO "
              "(or use --dry-run / --html-out to preview).")
    print(f"\n{DISCLAIMER}")
    return 0


def cmd_validate(args) -> int:
    from .engine.validate import render_validation

    settings = _settings_from_args(args)
    tickers_arg = getattr(args, "tickers", None) or ",".join(settings.watchlist[:5])
    tickers = [t.strip() for t in tickers_arg.split(",") if t.strip()]
    print(render_validation(tickers, settings))
    return 0


def cmd_dashboard(args) -> int:
    import subprocess
    from pathlib import Path

    app = Path(__file__).parent / "dash" / "streamlit_app.py"
    try:
        subprocess.run(["streamlit", "run", str(app)], check=False)
    except FileNotFoundError:
        print("Streamlit is not installed. Install with: pip install streamlit")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opportunity_engine",
        description="Research-first investment opportunity scanner. " + DISCLAIMER,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, helptext in [
        ("scan", cmd_scan, "Run a scan and print the ranked watchlist"),
        ("report", cmd_report, "Run a scan and write Markdown/CSV/JSON reports"),
        ("detail", cmd_detail, "Print full per-opportunity detail blocks"),
        ("backfill", cmd_backfill, "Snapshot scan scores into SQLite history"),
        ("portfolio", cmd_portfolio, "Build model portfolios from the scan"),
        ("validate", cmd_validate, "Validate data sources / readiness for tickers"),
        ("email", cmd_email, "Scan and email the full report (>=20 candidates)"),
        ("dashboard", cmd_dashboard, "Launch the Streamlit dashboard"),
    ]:
        p = sub.add_parser(name, help=helptext)
        _add_common(p)
        if name == "email":
            p.add_argument("--to", default=None, help="override recipient email")
            p.add_argument("--dry-run", action="store_true",
                           help="render but do not send")
            p.add_argument("--html-out", default=None,
                           help="write the HTML email to a file for preview")
        p.set_defaults(func=fn)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
