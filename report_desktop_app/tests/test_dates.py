"""Tests for shared date helpers."""

from __future__ import annotations

from datetime import date

from app.core.dates import format_period_display, period_bounds, period_label_for_filename


def test_period_bounds_daily() -> None:
    day = date(2026, 5, 18)
    start, end = period_bounds("daily", {"date": day})
    assert start == end == day


def test_period_bounds_monthly() -> None:
    month = date(2026, 5, 1)
    start, end = period_bounds("monthly", {"month": month})
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 31)


def test_period_label_for_filename_weekly() -> None:
    label = period_label_for_filename(
        "weekly",
        {"start": date(2026, 5, 12), "end": date(2026, 5, 18)},
    )
    assert label == "2026-05-12_to_2026-05-18"


def test_format_period_display_weekly() -> None:
    text = format_period_display(
        "weekly",
        {"start": date(2026, 5, 12), "end": date(2026, 5, 18)},
    )
    assert "2026-05-12" in text and "2026-05-18" in text
