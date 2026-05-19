"""Build weekly report tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from reporting.aggregation.weekly import aggregate_weekly
from reporting.config_loader import load_app_config
from reporting.reports.base import build_tables_from_aggregation


def build_weekly_report(
    canonical: pd.DataFrame,
    date_spec: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    cfg = load_app_config()
    tables = aggregate_weekly(canonical)
    return build_tables_from_aggregation(tables, cfg.reports["weekly"])
