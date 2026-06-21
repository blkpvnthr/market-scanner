"""Email engine.

Renders the daily watchlist as a self-contained HTML email and sends it over
SMTP. The emailed report always contains **at least 20 candidates ranked from
best to worst by maximum modelled return** (upside to target T3), and attaches
the CSV and JSON exports.

Everything degrades gracefully: with no SMTP credentials the message is rendered
but not sent (``dry_run`` / missing-config path), so the pipeline never crashes.

Research only. Not financial advice.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape

from ..config import Settings
from ..engine.pipeline import ScanResult
from ..models import DISCLAIMER, Opportunity
from .writers import render_csv, render_json, _flag_summary

MIN_CANDIDATES = 20


@dataclass
class EmailResult:
    sent: bool
    recipient: str | None
    candidate_count: int
    subject: str
    reason: str = ""


def select_candidates(result: ScanResult, limit: int | None = None) -> list[Opportunity]:
    """Return candidates ordered best->worst by max return, at least 20 of them."""
    target = max(MIN_CANDIDATES, limit or result.settings.email_top_n)
    ordered = sorted(result.opportunities, key=lambda o: o.max_return_pct, reverse=True)
    return ordered[:target]


def render_subject(result: ScanResult, candidates: list[Opportunity]) -> str:
    return (f"Opportunity Engine — {result.as_of.isoformat()} — "
            f"Top {len(candidates)} candidates by max return ({result.provider})")


def _money(x: float) -> str:
    return f"${x:,.2f}" if abs(x) < 1000 else f"${x:,.0f}"


def _summary_table(candidates: list[Opportunity]) -> str:
    head = (
        "<tr style='background:#0f172a;color:#fff;text-align:left'>"
        + "".join(f"<th style='padding:6px 10px;font:600 12px sans-serif'>{h}</th>" for h in
                  ["#", "Ticker", "Company", "Sector", "Price", "Max Ret %", "Exp Upside %",
                   "R/R", "Risk", "Score", "Top Catalyst", "Data"])
        + "</tr>"
    )
    rows = []
    for i, o in enumerate(candidates, start=1):
        cat = o.catalyst.catalysts[0].description if o.catalyst.catalysts else "-"
        flag = (o.provenance.flags or ["MOCK_DATA"])[0]
        bg = "#f8fafc" if i % 2 else "#ffffff"
        rows.append(
            f"<tr style='background:{bg}'>"
            f"<td style='padding:5px 10px;font:13px sans-serif'>{i}</td>"
            f"<td style='padding:5px 10px;font:700 13px sans-serif'>{escape(o.ticker)}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{escape(o.company)}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{escape(o.sector)}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{_money(o.current_price)}</td>"
            f"<td style='padding:5px 10px;font:700 13px sans-serif;color:#047857'>{o.max_return_pct:.1f}%</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{o.expected_upside_pct:.1f}%</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{o.plan.risk_reward_ratio:.1f}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{escape(o.risk.level.value)}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{o.scores.final_score:.0f}</td>"
            f"<td style='padding:5px 10px;font:12px sans-serif'>{escape(cat[:48])}</td>"
            f"<td style='padding:5px 10px;font:11px sans-serif;color:#64748b'>{escape(flag)}</td>"
            "</tr>"
        )
    return ("<table style='border-collapse:collapse;width:100%;border:1px solid #e2e8f0'>"
            + head + "".join(rows) + "</table>")


def _detail_block(i: int, o: Opportunity) -> str:
    p = o.plan
    a = o.analyst
    cats = "".join(
        f"<li style='margin:2px 0'>[{escape(c.type.value)}] {escape(c.description)} "
        f"({c.confidence:.0%})</li>" for c in o.catalyst.catalysts[:5]
    )
    analyst_line = (
        f"Low {_money(a.target_low or 0)} · Mean {_money(a.target_mean or 0)} · "
        f"High {_money(a.target_high or 0)} ({a.num_analysts} analysts)"
        if a.target_mean else "n/a"
    )
    return (
        f"<div style='margin:18px 0;padding:14px;border:1px solid #e2e8f0;border-radius:8px'>"
        f"<h3 style='margin:0 0 4px;font:700 16px sans-serif'>"
        f"#{i} {escape(o.ticker)} — {escape(o.company)} "
        f"<span style='color:#047857'>(max ret {o.max_return_pct:.1f}%)</span></h3>"
        f"<div style='font:12px sans-serif;color:#64748b;margin-bottom:8px'>"
        f"{escape(o.sector)} · Score {o.scores.final_score:.0f}/100 · Risk {escape(o.risk.level.value)} · "
        f"Hold {escape(p.holding_period)} · Data: {escape(', '.join(o.provenance.flags) or 'MOCK_DATA')}</div>"
        f"<table style='font:12px sans-serif;border-collapse:collapse'>"
        f"<tr><td style='padding:2px 12px 2px 0'><b>Price</b></td><td>{_money(o.current_price)}</td>"
        f"<td style='padding:2px 12px'><b>Entries</b></td>"
        f"<td>Aggr {_money(p.aggressive_entry)} · Base {_money(p.base_entry)} · "
        f"Cons {_money(p.conservative_entry)}</td></tr>"
        f"<tr><td style='padding:2px 12px 2px 0'><b>Stop</b></td><td>{_money(p.stop_loss)}</td>"
        f"<td style='padding:2px 12px'><b>Targets</b></td>"
        f"<td>{_money(p.target_1)} · {_money(p.target_2)} · {_money(p.target_3)}</td></tr>"
        f"<tr><td style='padding:2px 12px 2px 0'><b>Analyst</b></td><td colspan='3'>{analyst_line}</td></tr>"
        f"<tr><td style='padding:2px 12px 2px 0'><b>R/R</b></td><td>{p.risk_reward_ratio:.1f}:1</td>"
        f"<td style='padding:2px 12px'><b>Max DD est</b></td><td>{p.max_drawdown_estimate:.1f}%</td></tr>"
        f"</table>"
        f"<p style='font:12px sans-serif;margin:8px 0 4px'><b>Thesis:</b> {escape(o.thesis.summary)}</p>"
        f"<p style='font:12px sans-serif;margin:2px 0'><b>Bull:</b> {escape(o.thesis.bull_case)}</p>"
        f"<p style='font:12px sans-serif;margin:2px 0'><b>Base:</b> {escape(o.thesis.base_case)}</p>"
        f"<p style='font:12px sans-serif;margin:2px 0'><b>Bear:</b> {escape(o.thesis.bear_case)}</p>"
        f"<p style='font:12px sans-serif;margin:6px 0 2px'><b>Catalysts:</b></p>"
        f"<ul style='font:12px sans-serif;margin:0 0 6px;padding-left:18px'>{cats}</ul>"
        f"<p style='font:12px sans-serif;margin:2px 0'><b>Key risks:</b> "
        f"{escape('; '.join(o.thesis.key_risks))}</p>"
        f"</div>"
    )


def render_email_html(result: ScanResult, limit: int | None = None) -> str:
    candidates = select_candidates(result, limit)
    counts = _flag_summary(result)
    dq = " · ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "MOCK_DATA"
    details = "".join(_detail_block(i, o) for i, o in enumerate(candidates, start=1))
    return (
        "<html><body style='background:#f1f5f9;margin:0;padding:20px'>"
        "<div style='max-width:980px;margin:0 auto;background:#fff;padding:24px;"
        "border-radius:12px'>"
        f"<h1 style='font:700 22px sans-serif;margin:0 0 4px'>📈 Opportunity Engine</h1>"
        f"<div style='font:13px sans-serif;color:#475569;margin-bottom:4px'>"
        f"Daily watchlist · {result.as_of.isoformat()} · provider: {escape(result.provider)} · "
        f"{len(candidates)} candidates ranked best→worst by max return</div>"
        f"<div style='font:12px sans-serif;color:#64748b;margin-bottom:14px'>Data quality: {dq}</div>"
        f"<div style='background:#fef3c7;border:1px solid #f59e0b;padding:8px 12px;"
        f"border-radius:6px;font:600 12px sans-serif;color:#92400e;margin-bottom:16px'>"
        f"⚠ {DISCLAIMER}</div>"
        f"{_summary_table(candidates)}"
        f"<h2 style='font:700 18px sans-serif;margin:24px 0 8px'>Candidate Detail</h2>"
        f"{details}"
        f"<div style='font:11px sans-serif;color:#94a3b8;margin-top:18px;text-align:center'>"
        f"{DISCLAIMER} · No automated trading or order execution.</div>"
        "</div></body></html>"
    )


def build_message(result: ScanResult, settings: Settings,
                  limit: int | None = None) -> tuple[EmailMessage, list[Opportunity]]:
    candidates = select_candidates(result, limit)
    msg = EmailMessage()
    msg["Subject"] = render_subject(result, candidates)
    msg["From"] = settings.email_from or "opportunity-engine@localhost"
    msg["To"] = settings.email_to or ""
    # Plain-text fallback + HTML alternative.
    msg.set_content(
        f"Opportunity Engine — {result.as_of.isoformat()} ({result.provider})\n"
        f"{len(candidates)} candidates ranked best->worst by max return.\n"
        f"View this email in an HTML-capable client for the full report.\n\n{DISCLAIMER}\n"
    )
    msg.add_alternative(render_email_html(result, limit), subtype="html")
    # Attach CSV + JSON exports.
    stamp = result.as_of.isoformat()
    msg.add_attachment(render_csv(result).encode(), maintype="text", subtype="csv",
                       filename=f"watchlist_{stamp}.csv")
    msg.add_attachment(render_json(result).encode(), maintype="application", subtype="json",
                       filename=f"watchlist_{stamp}.json")
    return msg, candidates


def send_report_email(result: ScanResult, settings: Settings,
                      limit: int | None = None, dry_run: bool = False) -> EmailResult:
    msg, candidates = build_message(result, settings, limit)
    subject = msg["Subject"]

    if dry_run:
        return EmailResult(False, settings.email_to, len(candidates), subject, "dry-run")
    if not settings.has_email:
        return EmailResult(False, settings.email_to, len(candidates), subject,
                           "SMTP not configured (set SMTP_HOST/SMTP_USER/SMTP_PASSWORD/"
                           "EMAIL_FROM/EMAIL_TO)")

    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
    try:
        server.ehlo()
        if settings.smtp_starttls:
            server.starttls()
            server.ehlo()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return EmailResult(True, settings.email_to, len(candidates), subject, "sent")
