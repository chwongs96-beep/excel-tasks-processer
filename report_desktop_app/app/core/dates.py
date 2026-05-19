"""Shared date helpers — delegates to parent reporting.core.dates."""

from __future__ import annotations

from app.core.reporting_bridge import ensure_reporting_package

ensure_reporting_package()

from reporting.core.dates import (  # noqa: E402
    as_date,
    format_period_display,
    period_bounds,
    period_label_for_filename,
)

__all__ = [
    "as_date",
    "format_period_display",
    "period_bounds",
    "period_label_for_filename",
]
