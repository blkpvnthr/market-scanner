"""Report generation: Markdown, CSV, JSON and themed sub-reports.

Research only. Not financial advice.
"""

from .writers import (
    write_all_reports,
    render_daily_markdown,
    render_csv,
    render_json,
    render_catalyst_report,
    render_ipo_report,
    render_earnings_report,
    render_sector_report,
)

__all__ = [
    "write_all_reports",
    "render_daily_markdown",
    "render_csv",
    "render_json",
    "render_catalyst_report",
    "render_ipo_report",
    "render_earnings_report",
    "render_sector_report",
]
