"""Report rendering tests. Research only. Not financial advice."""

from __future__ import annotations

import csv
import io
import json

from opportunity_engine.models import DISCLAIMER
from opportunity_engine.reports import (
    render_catalyst_report,
    render_csv,
    render_daily_markdown,
    render_earnings_report,
    render_ipo_report,
    render_json,
    render_sector_report,
)
from opportunity_engine.reports.writers import CSV_COLUMNS, write_all_reports


def test_markdown_contains_disclaimer_and_ranks(scan_result):
    md = render_daily_markdown(scan_result)
    assert DISCLAIMER in md
    assert "#1 " in md
    assert "Thesis:" in md


def test_csv_has_all_columns_and_rows(scan_result):
    text = render_csv(scan_result)
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == CSV_COLUMNS
    rows = list(reader)
    assert len(rows) == len(scan_result.opportunities)
    assert rows[0]["ticker"]


def test_json_roundtrip(scan_result):
    payload = json.loads(render_json(scan_result))
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["count"] == len(scan_result.opportunities)
    assert payload["opportunities"][0]["scores"]["final_score"] >= \
           payload["opportunities"][-1]["scores"]["final_score"]


def test_themed_reports_render(scan_result):
    for fn in (render_sector_report, render_catalyst_report,
               render_ipo_report, render_earnings_report):
        out = fn(scan_result)
        assert DISCLAIMER in out
        assert out.strip()


def test_write_all_reports(tmp_path, scan_result):
    written = write_all_reports(scan_result, str(tmp_path))
    assert len(written) == 8
    for path in written.values():
        from pathlib import Path

        assert Path(path).exists()
        assert Path(path).stat().st_size > 0
