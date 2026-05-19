"""
Transformation layer: raw Excel DataFrames -> canonical schema -> report tables.

Assumptions (see module docstring in project README):
- First worksheet only; headers on row 1.
- Primary date field is trade_date (filter_field in report_definitions.yaml).
- Amount may be derived from debit - credit when amount is empty.
- Weekly period uses inclusive start/end from UI (calendar week).
- Monthly period uses full calendar month of the selected month.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from app.core import config
from app.core.dates import period_bounds
from app.core.logger import get_logger
from app.core.reporting_bridge import ensure_reporting_package
from app.core.schemas import (
    DateSpec,
    ReportDefinition,
    ReportOutputSpec,
    ReportType,
    TransformResult,
)

ensure_reporting_package()
from reporting.validation.date_validator import parse_dates  # noqa: E402

ReportTables = dict[str, pd.DataFrame]
logger = get_logger()


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------


def resolve_rename_map(
    source_columns: list[str],
    *,
    manual_mapping: dict[str, str] | None = None,
    filename: str | None = None,
) -> dict[str, str]:
    """Prefer manual per-file mapping; otherwise alias table from config."""
    if manual_mapping and filename:
        manual = config.build_manual_rename_map(manual_mapping, filename)
        if manual:
            return manual
    return config.build_alias_rename_map(source_columns)


def rename_to_standard_columns(
    frame: pd.DataFrame,
    rename_map: dict[str, str],
) -> pd.DataFrame:
    """Rename to canonical names; add missing optional columns as NA."""
    renamed = frame.rename(columns=rename_map)
    for field in config.CANONICAL_FIELDS:
        if field not in renamed.columns:
            renamed[field] = pd.NA
    return renamed[list(config.CANONICAL_FIELDS)]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def parse_and_normalize_dates(
    frame: pd.DataFrame,
    date_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    out = frame.copy()
    for column in date_columns or config.DATE_COLUMNS:
        if column in out.columns:
            out[column] = parse_dates(out[column])
    return out


def clean_text_columns(
    frame: pd.DataFrame,
    text_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    out = frame.copy()
    for column in text_columns or config.TEXT_COLUMNS:
        if column in out.columns:
            out[column] = out[column].astype("string").str.strip()
    return out


def convert_numeric_columns(
    frame: pd.DataFrame,
    numeric_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    out = frame.copy()
    for column in numeric_columns or config.NUMERIC_COLUMNS:
        if column in out.columns:
            out[column] = _safe_numeric(out[column])
    return out


def derive_amount_if_missing(frame: pd.DataFrame) -> pd.DataFrame:
    """When amount is entirely empty, use debit - credit if both exist."""
    out = frame.copy()
    if "amount" not in out.columns or out["amount"].notna().any():
        return out
    if {"debit", "credit"}.issubset(out.columns):
        out["amount"] = out["debit"].fillna(0) - out["credit"].fillna(0)
    return out


def _safe_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace({"nan": None, "None": None, "": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def transform_raw_dataframe(
    frame: pd.DataFrame,
    *,
    manual_mapping: dict[str, str] | None = None,
    filename: str | None = None,
) -> pd.DataFrame:
    """Map headers, normalize types, clean values (no period filter)."""
    rename_map = resolve_rename_map(
        [str(c) for c in frame.columns],
        manual_mapping=manual_mapping,
        filename=filename,
    )
    canonical = rename_to_standard_columns(frame, rename_map)
    canonical = parse_and_normalize_dates(canonical)
    canonical = convert_numeric_columns(canonical)
    canonical = clean_text_columns(canonical)
    return derive_amount_if_missing(canonical)


# ---------------------------------------------------------------------------
# Period filter
# ---------------------------------------------------------------------------


def filter_by_date_range(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
    *,
    date_field: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Keep rows whose date_field falls in the selected period (inclusive).

    Returns (filtered_frame, warnings). Empty result adds a warning message.
    """
    report_def = config.get_report_definition(report_type)
    field = date_field or report_def.filter_field
    if field not in frame.columns:
        return frame, []

    start, end = period_bounds(report_type, date_spec)
    series = pd.to_datetime(frame[field], errors="coerce")
    mask = (series >= pd.Timestamp(start)) & (series <= pd.Timestamp(end))
    filtered = frame.loc[mask].copy()

    warnings: list[str] = []
    if filtered.empty:
        warnings.append(
            f"選定區間內無符合資料（{start.isoformat()} 至 {end.isoformat()}）。"
            "請調整日期或檢查來源檔。"
        )
    return filtered, warnings


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_output_table(frame: pd.DataFrame, output: ReportOutputSpec) -> pd.DataFrame:
    """Build one output table from a report output spec."""
    if not output.group_by:
        cols = [c for c in frame.columns if c in config.CANONICAL_FIELDS or c == "_source_file"]
        return frame[cols].copy() if cols else frame.copy()

    grouped = frame.groupby(list(output.group_by), dropna=False)
    agg_spec = {
        column: func
        for column, func in output.measures.items()
        if column in frame.columns
    }
    if not agg_spec:
        return grouped.size().reset_index(name="row_count")
    return grouped.agg(agg_spec).reset_index()


def aggregate_for_report_type(
    frame: pd.DataFrame,
    report_type: ReportType,
) -> ReportTables:
    """Aggregate filtered canonical data into all configured tables."""
    report_def = config.get_report_definition(report_type)
    tables: ReportTables = {}
    for output in report_def.outputs:
        tables[output.id] = aggregate_output_table(frame, output)
    return tables


def apply_report_titles(tables: ReportTables, report_type: ReportType) -> ReportTables:
    """Use human-readable titles as dict keys for UI / export."""
    outputs = {o.id: o for o in config.get_report_definition(report_type).outputs}
    return {
        (outputs[key].title if key in outputs else key): df
        for key, df in tables.items()
    }


def transform_for_report(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
) -> TransformResult:
    """
    Normalize canonical frame, filter by period, aggregate per report type.

    Input frame should already be canonical (or will be re-normalized).
    """
    warnings: list[str] = []

    normalized = parse_and_normalize_dates(frame)
    normalized = convert_numeric_columns(normalized)
    normalized = clean_text_columns(normalized)
    normalized = derive_amount_if_missing(normalized)

    if "trade_date" in normalized.columns:
        invalid = int(normalized["trade_date"].isna().sum())
        if invalid:
            warnings.append(f"有 {invalid} 列交易日期無法解析，已略過於日期篩選。")

    filtered, filter_warnings = filter_by_date_range(normalized, report_type, date_spec)
    warnings.extend(filter_warnings)

    if filtered.empty:
        return TransformResult(
            tables={},
            warnings=warnings,
            blocking=True,
            blocking_message=filter_warnings[0] if filter_warnings else "選定區間內無資料。",
        )

    tables = aggregate_for_report_type(filtered, report_type)
    titled = apply_report_titles(tables, report_type)
    return TransformResult(tables=titled, warnings=warnings)


# ---------------------------------------------------------------------------
# Service facade
# ---------------------------------------------------------------------------


class TransformerService:
    """Facade used by AppController and report pipeline."""

    def to_canonical(
        self,
        frame: pd.DataFrame,
        mapping: dict[str, str],
        *,
        source_name: str = "",
    ) -> pd.DataFrame:
        return transform_raw_dataframe(
            frame,
            manual_mapping=mapping or None,
            filename=source_name or None,
        )

    def build_report_tables(
        self,
        canonical: pd.DataFrame,
        report_type: ReportType,
        date_spec: DateSpec | dict[str, Any],
    ) -> TransformResult:
        spec_dict = date_spec.to_dict() if isinstance(date_spec, DateSpec) else date_spec
        return transform_for_report(canonical, report_type, spec_dict)
