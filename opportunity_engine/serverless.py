"""Serverless entrypoints.

A single handler that runs the scan and emails the report, suitable for any
schedule-driven serverless runtime (AWS Lambda + EventBridge, GCP Cloud
Functions + Cloud Scheduler, Azure Functions, etc.). Configuration comes
entirely from environment variables, so no laptop is required for delivery.

    AWS Lambda handler:  opportunity_engine.serverless.lambda_handler
    Generic / cron:      python -m opportunity_engine.serverless

Research only. Not financial advice.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .config import load_settings
from .engine import run_scan
from .reports.email import send_report_email


def run_and_email(provider: str | None = None) -> dict[str, Any]:
    """Run a scan and email the report. Returns a JSON-serializable summary."""
    settings = load_settings()
    if provider or os.getenv("OE_PROVIDER"):
        settings.provider = provider or os.environ["OE_PROVIDER"]
    # Guarantee a >=20-candidate report and a large-enough universe.
    settings.email_top_n = max(20, settings.email_top_n)
    if settings.max_universe < 25:
        settings.max_universe = 60

    result = run_scan(settings)
    res = send_report_email(result, settings)
    return {
        "sent": res.sent,
        "recipient": res.recipient,
        "candidates": res.candidate_count,
        "subject": res.subject,
        "reason": res.reason,
        "provider": result.provider,
        "as_of": result.as_of.isoformat(),
        "disclaimer": "Research only. Not financial advice.",
    }


def lambda_handler(event: Any = None, context: Any = None) -> dict[str, Any]:
    """AWS Lambda entrypoint. ``event``/``context`` are accepted but unused."""
    summary = run_and_email()
    return {"statusCode": 200 if summary["sent"] else 202, "body": json.dumps(summary)}


def main() -> int:
    summary = run_and_email()
    print(json.dumps(summary, indent=2))
    return 0 if summary["sent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
