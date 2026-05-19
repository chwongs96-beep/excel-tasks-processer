"""Tests for reporting.core.filenames."""

from __future__ import annotations

from datetime import date

from reporting.core.filenames import build_output_filename


def test_build_output_filename_uses_template() -> None:
    name = build_output_filename(
        "daily",
        {"date": date(2026, 5, 1)},
        filename_template="{report_type}_{period_label}.xlsx",
    )
    assert name == "daily_2026-05-01.xlsx"
