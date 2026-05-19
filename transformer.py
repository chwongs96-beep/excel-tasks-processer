"""
Transformation layer: raw Excel DataFrames -> unified schema -> report-ready tables.

No UI dependencies. Configuration comes from config.py (backed by config/*.yaml).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

import app_config as config
from reporting.config_loader import OutputDef, ReportDef, load_app_config
from reporting.core.dates import period_bounds
from reporting.models import ReportType, ValidationIssue
from reporting.validation.date_validator import parse_dates

ReportTables = dict[str, pd.DataFrame]


# ---------------------------------------------------------------------------
# Column renaming & canonical frame
# ---------------------------------------------------------------------------


def rename_to_standard_columns(
    frame: pd.DataFrame,
    rename_map: dict[str, str],
) -> pd.DataFrame:
    """
    Rename source headers to canonical names and ensure all schema columns exist.

    Missing optional columns are added as NA.
    """
    renamed = frame.rename(columns=rename_map)
    for field in config.CANONICAL_FIELDS:
        if field not in renamed.columns:
            renamed[field] = pd.NA
    return renamed[list(config.CANONICAL_FIELDS)]


def resolve_rename_map(
    source_columns: list[str],
    *,
    manual_mapping: dict[str, str] | None = None,
    filename: str | None = None,
) -> dict[str, str]:
    """Prefer manual per-file mapping; fall back to alias table."""
    if manual_mapping and filename:
        manual = config.build_manual_rename_map(manual_mapping, filename)
        if manual:
            return manual
    return config.build_alias_rename_map(source_columns)


def transform_raw_dataframe(
    frame: pd.DataFrame,
    *,
    manual_mapping: dict[str, str] | None = None,
    filename: str | None = None,
) -> pd.DataFrame:
    """Map, normalize types, and clean a single raw upload (no date filter)."""
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
# Type normalization
# ---------------------------------------------------------------------------


def parse_and_normalize_dates(
    frame: pd.DataFrame,
    date_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Parse date columns to datetime64; missing columns are skipped."""
    date_columns = date_columns or config.DATE_COLUMNS
    out = frame.copy()
    for column in date_columns:
        if column in out.columns:
            out[column] = parse_dates(out[column])
    return out


def clean_text_columns(
    frame: pd.DataFrame,
    text_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Strip whitespace on string-like canonical columns."""
    text_columns = text_columns or config.TEXT_COLUMNS
    out = frame.copy()
    for column in text_columns:
        if column in out.columns:
            out[column] = out[column].astype("string").str.strip()
    return out


def convert_numeric_columns(
    frame: pd.DataFrame,
    numeric_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Safely coerce numeric columns (handles commas and blanks)."""
    numeric_columns = numeric_columns or config.NUMERIC_COLUMNS
    out = frame.copy()
    for column in numeric_columns:
        if column in out.columns:
            out[column] = _safe_numeric(out[column])
    return out


def derive_amount_if_missing(frame: pd.DataFrame) -> pd.DataFrame:
    """Fill amount from debit/credit when amount is entirely empty."""
    out = frame.copy()
    if "amount" not in out.columns:
        return out
    if out["amount"].notna().any():
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


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------


def filter_by_date_range(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
    *,
    date_field: str | None = None,
) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Keep rows whose trade_date (or configured field) falls in the selected period."""
    cfg = load_app_config()
    report_def = cfg.reports.get(report_type)
    if report_def is None:
        return frame, [
            ValidationIssue(
                code="unknown_report_type",
                message=f"未知的報表類型：{report_type}",
            )
        ]

    field = date_field or report_def.filter_field
    if field not in frame.columns:
        return frame, []

    start, end = period_bounds(report_type, date_spec)
    series = pd.to_datetime(frame[field], errors="coerce")
    mask = (series >= pd.Timestamp(start)) & (series <= pd.Timestamp(end))
    filtered = frame.loc[mask].copy()

    issues: list[ValidationIssue] = []
    if filtered.empty:
        issues.append(
            ValidationIssue(
                code="no_data_in_period",
                message="選定區間內無符合資料，請確認日期或上傳內容。",
                details={"start": start.isoformat(), "end": end.isoformat()},
            )
        )
    return filtered, issues


# ---------------------------------------------------------------------------
# Aggregation (daily / weekly / monthly)
# ---------------------------------------------------------------------------


def aggregate_output_table(frame: pd.DataFrame, output: OutputDef) -> pd.DataFrame:
    """Build one summary/detail table from report_definitions output spec."""
    if not output.group_by:
        cols = [c for c in frame.columns if c in config.CANONICAL_FIELDS or c == "_source_file"]
        return frame[cols].copy() if cols else frame.copy()

    grouped = frame.groupby(output.group_by, dropna=False)
    agg_spec: dict[str, str] = {}
    for column, func in output.measures.items():
        if column in frame.columns:
            agg_spec[column] = func

    if not agg_spec:
        return grouped.size().reset_index(name="row_count")

    return grouped.agg(agg_spec).reset_index()


def aggregate_for_report_type(
    frame: pd.DataFrame,
    report_type: ReportType,
) -> ReportTables:
    """Aggregate canonical data into all configured tables for the report type."""
    report_def = config.REPORT_DEFINITIONS[report_type]
    return _aggregate_with_definition(frame, report_def)


def _aggregate_with_definition(frame: pd.DataFrame, report_def: ReportDef) -> ReportTables:
    tables: ReportTables = {}
    for output in report_def.outputs:
        tables[output.id] = aggregate_output_table(frame, output)
    return tables


def apply_report_titles(tables: ReportTables, report_type: ReportType) -> ReportTables:
    """Use human-readable output titles as dict keys for export/display."""
    outputs = {o.id: o for o in config.get_report_outputs(report_type)}
    return {
        (outputs[key].title if key in outputs else key): df
        for key, df in tables.items()
    }


# ---------------------------------------------------------------------------
# End-to-end transform for reporting pipeline
# ---------------------------------------------------------------------------


def transform_for_report(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
    *,
    skip_normalize: bool = False,
) -> tuple[ReportTables, list[ValidationIssue], list[str]]:
    """
    Normalize an already-canonical merged frame, filter by period, and aggregate.

    Args:
        frame: Merged canonical DataFrame (may include _source_file).
        report_type: daily | weekly | monthly.
        date_spec: Sidebar date selection dict.
        skip_normalize: When True, assume ``normalize_canonical_frame`` already ran.

    Returns:
        (report_tables, validation_issues, warning_messages)
    """
    warnings: list[str] = []

    if skip_normalize:
        normalized = frame.copy()
    else:
        normalized = parse_and_normalize_dates(frame)
        normalized = convert_numeric_columns(normalized)
        normalized = clean_text_columns(normalized)
        normalized = derive_amount_if_missing(normalized)

    if "trade_date" in normalized.columns:
        invalid = int(normalized["trade_date"].isna().sum())
        if invalid:
            warnings.append(f"有 {invalid} 列 trade_date 無法解析。")

    filtered, issues = filter_by_date_range(normalized, report_type, date_spec)
    if filtered.empty and issues:
        return {}, issues, warnings

    tables = aggregate_for_report_type(filtered, report_type)
    titled = apply_report_titles(tables, report_type)
    return titled, issues, warnings


def transform_merged_upload(
    frame: pd.DataFrame,
    report_type: ReportType,
    date_spec: dict[str, Any],
) -> tuple[ReportTables, list[ValidationIssue], list[str]]:
    """
    Full post-load pipeline: normalize merged canonical data then report aggregate.

    Use when file_bundle has already applied column mapping.
    """
    return transform_for_report(frame, report_type, date_spec)
