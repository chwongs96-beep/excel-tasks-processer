"""Build monthly report tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from reporting.aggregation.monthly import aggregate_monthly
from reporting.config_loader import load_app_config
from reporting.reports.base import build_tables_from_aggregation


def build_monthly_report(
    canonical: pd.DataFrame,
    date_spec: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    cfg = load_app_config()
    tables = aggregate_monthly(canonical)
    return build_tables_from_aggregation(tables, cfg.reports["monthly"])
