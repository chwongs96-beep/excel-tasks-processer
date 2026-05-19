"""Shared date range and filename label helpers for pipeline, transformer, and export."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

from reporting.models import ReportType


def as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def period_bounds(report_type: ReportType, date_spec: dict[str, Any]) -> tuple[date, date]:
    """Inclusive start/end for daily, weekly, or monthly selection."""
    if report_type == "daily":
        day = as_date(date_spec["date"])
        return day, day
    if report_type == "weekly":
        return as_date(date_spec["start"]), as_date(date_spec["end"])
    month = as_date(date_spec["month"])
    last_day = calendar.monthrange(month.year, month.month)[1]
    return date(month.year, month.month, 1), date(month.year, month.month, last_day)


def period_label_for_filename(report_type: ReportType, date_spec: dict[str, Any]) -> str:
    """Short label used in output filenames."""
    if report_type == "daily":
        return _fmt_iso(date_spec.get("date"))
    if report_type == "weekly":
        return f"{_fmt_iso(date_spec.get('start'))}_to_{_fmt_iso(date_spec.get('end'))}"
    month = date_spec.get("month")
    if month:
        if isinstance(month, datetime):
            month = month.date()
        elif not isinstance(month, date):
            month = as_date(month)
        return month.strftime("%Y-%m")
    return "unknown"


def format_period_display(
    report_type: ReportType,
    date_spec: dict[str, Any],
    *,
    start: date | None = None,
    end: date | None = None,
) -> str:
    """Human-readable period for template metadata cells."""
    if start is None or end is None:
        start, end = period_bounds(report_type, date_spec)
    if report_type == "daily":
        return start.isoformat()
    if report_type == "weekly":
        return f"{start.isoformat()} ~ {end.isoformat()}"
    return start.strftime("%Y-%m")


def _fmt_iso(value: date | datetime | None) -> str:
    if value is None:
        return "unknown"
    return as_date(value).isoformat()
