"""Shared report building context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from reporting.config_loader import ReportDef
from reporting.models import ReportType


@dataclass
class ReportContext:
    report_type: ReportType
    date_spec: dict[str, Any]
    canonical: pd.DataFrame
    report_def: ReportDef


def build_tables_from_aggregation(
    tables: dict[str, pd.DataFrame],
    report_def: ReportDef,
) -> dict[str, pd.DataFrame]:
    """Attach human-readable titles as a leading metadata row is not needed; use sheet titles."""
    titled: dict[str, pd.DataFrame] = {}
    output_by_id = {o.id: o for o in report_def.outputs}
    for key, frame in tables.items():
        title = output_by_id.get(key, None)
        sheet_key = title.title if title else key
        titled[sheet_key] = frame
    return titled
