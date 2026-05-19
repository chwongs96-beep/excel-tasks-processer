"""Filter canonical data by report period — delegates to transformer.py."""

from __future__ import annotations

from typing import Any

import pandas as pd

import transformer as tx
from reporting.models import ReportType, ValidationIssue


def filter_by_report_period(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    return tx.filter_by_date_range(frame, report_type, date_spec)
