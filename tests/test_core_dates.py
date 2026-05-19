"""Tests for reporting.core.dates."""

from __future__ import annotations

from datetime import date

from reporting.core.dates import period_bounds, period_label_for_filename


def test_period_bounds_daily() -> None:
    start, end = period_bounds("daily", {"date": date(2026, 5, 1)})
    assert start == end == date(2026, 5, 1)


def test_period_label_weekly() -> None:
    label = period_label_for_filename(
        "weekly",
        {"start": date(2026, 5, 5), "end": date(2026, 5, 11)},
    )
    assert label == "2026-05-05_to_2026-05-11"
