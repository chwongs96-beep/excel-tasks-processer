"""Tests for batch date list helper."""

from __future__ import annotations

from datetime import date

from app.services.batch_report_service import dates_in_range


def test_dates_in_range_weekdays() -> None:
    # 2026-01-05 Mon .. 2026-01-11 Sun
    days = dates_in_range(date(2026, 1, 5), date(2026, 1, 11), business_days_only=True)
    assert len(days) == 5
    assert all(d.weekday() < 5 for d in days)
