"""Daily report aggregation."""

from __future__ import annotations

import pandas as pd

from reporting.aggregation._common import aggregate_for_report
from reporting.config_loader import load_app_config


def aggregate_daily(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cfg = load_app_config()
    return aggregate_for_report(frame, cfg.reports["daily"])
