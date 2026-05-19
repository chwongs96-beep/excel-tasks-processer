"""Shared core utilities (dates, safe I/O)."""

from reporting.core.dates import (
    as_date,
    format_period_display,
    period_bounds,
    period_label_for_filename,
)
from reporting.core.filenames import build_output_filename
from reporting.core.safe_io import atomic_save_workbook, secure_output_path

__all__ = [
    "as_date",
    "atomic_save_workbook",
    "build_output_filename",
    "format_period_display",
    "period_bounds",
    "period_label_for_filename",
    "secure_output_path",
]
