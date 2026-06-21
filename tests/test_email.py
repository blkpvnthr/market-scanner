"""Email engine tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.config import Settings
from opportunity_engine.engine.pipeline import run_scan
from opportunity_engine.reports import email as email_mod
from opportunity_engine.reports.email import (
    MIN_CANDIDATES,
    render_email_html,
    select_candidates,
    send_report_email,
)


def _result():
    return run_scan(Settings(provider="mock", top_n=10, max_universe=40, seed=7))


def test_at_least_20_candidates_ranked_by_max_return():
    result = _result()
    cands = select_candidates(result)
    assert len(cands) >= MIN_CANDIDATES
    mrs = [o.max_return_pct for o in cands]
    assert mrs == sorted(mrs, reverse=True)  # best -> worst by max return


def test_html_contains_disclaimer_and_all_candidates():
    result = _result()
    html = render_email_html(result)
    assert "Not financial advice" in html
    assert "Max Ret %" in html
    for o in select_candidates(result):
        assert o.ticker in html


def test_dry_run_does_not_send():
    result = _result()
    res = send_report_email(result, result.settings, dry_run=True)
    assert res.sent is False
    assert res.reason == "dry-run"
    assert res.candidate_count >= MIN_CANDIDATES


def test_missing_smtp_is_graceful():
    result = _result()
    res = send_report_email(result, result.settings)  # no SMTP configured
    assert res.sent is False
    assert "SMTP" in res.reason


def test_send_path_with_mocked_smtp(monkeypatch):
    """When configured, the send path logs in and dispatches the message."""
    calls = {"login": 0, "send": 0, "starttls": 0}

    class FakeSMTP:
        def __init__(self, host, port, timeout=30):
            calls["host"] = host
            calls["port"] = port

        def ehlo(self): pass
        def starttls(self): calls["starttls"] += 1
        def login(self, user, pw): calls["login"] += 1
        def send_message(self, msg):
            calls["send"] += 1
            calls["subject"] = msg["Subject"]
        def quit(self): pass

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)

    s = Settings(provider="mock", seed=7)
    s.smtp_host = "smtp.example.com"
    s.smtp_user = "u@example.com"
    s.smtp_password = "secret"
    s.email_from = "u@example.com"
    s.email_to = "me@example.com"
    assert s.has_email

    result = run_scan(s)
    res = send_report_email(result, s)
    assert res.sent is True
    assert calls["login"] == 1 and calls["send"] == 1 and calls["starttls"] == 1
    assert calls["host"] == "smtp.example.com"
    assert "max return" in calls["subject"]
