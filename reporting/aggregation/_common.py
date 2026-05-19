"""Shared aggregation helpers — delegates to transformer.py."""

from __future__ import annotations

import pandas as pd

import transformer as tx
from reporting.config_loader import OutputDef, ReportDef


def build_output_table(frame: pd.DataFrame, output: OutputDef) -> pd.DataFrame:
    return tx.aggregate_output_table(frame, output)


def aggregate_for_report(frame: pd.DataFrame, report_def: ReportDef) -> dict[str, pd.DataFrame]:
    return tx._aggregate_with_definition(frame, report_def)
