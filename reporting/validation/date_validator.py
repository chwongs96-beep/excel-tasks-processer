"""Date parsing and validation."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from reporting.config_loader import load_app_config
from reporting.models import ValidationIssue

DATE_PARSE_SUCCESS_RATIO = 0.8


def parse_dates(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.5:
        return pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
    with pd.option_context("mode.chained_assignment", None):
        return pd.to_datetime(series.astype(str), errors="coerce", format="mixed")


def validate_date_columns(
    frame: pd.DataFrame,
    filename: str | None = None,
) -> list[ValidationIssue]:
    cfg = load_app_config()
    issues: list[ValidationIssue] = []
    prefix = f"{filename}: " if filename else ""

    for column in cfg.schema.date_columns:
        if column not in frame.columns:
            continue
        series = frame[column].dropna()
        if series.empty:
            issues.append(
                ValidationIssue(
                    code="invalid_date_column",
                    message=f"{prefix}日期欄位「{column}」沒有可解析的資料。",
                    filename=filename,
                    column=column,
                )
            )
            continue

        parsed = parse_dates(series)
        success_ratio = float(parsed.notna().mean())
        if success_ratio < DATE_PARSE_SUCCESS_RATIO:
            issues.append(
                ValidationIssue(
                    code="invalid_date_column",
                    message=(
                        f"{prefix}日期欄位「{column}」格式無效"
                        f"（可解析 {success_ratio:.0%}，"
                        f"需要至少 {DATE_PARSE_SUCCESS_RATIO:.0%}）。"
                    ),
                    filename=filename,
                    column=column,
                    details={
                        "success_ratio": success_ratio,
                        "sample_invalid": raw[parsed.isna()].astype(str).head(3).tolist()
                        if (raw := series).notna().any()
                        else [],
                    },
                )
            )
    return issues


def validate_merged_duplicates(frame: pd.DataFrame) -> tuple[list[ValidationIssue], int]:
    cfg = load_app_config()
    subset = tuple(cfg.schema.duplicate_subset)
    available = [col for col in subset if col in frame.columns]
    if not available or frame.empty:
        return [], 0

    mask = frame.duplicated(subset=available, keep=False)
    count = int(mask.sum())
    if count == 0:
        return [], 0

    return [
        ValidationIssue(
            code="duplicate_rows",
            message=(
                f"合併後資料有 {count} 列重複（比對欄位：{', '.join(available)}）。"
            ),
            details={"duplicate_count": count, "subset": available},
        )
    ], count


def validate_date_selection(report_type: str, date_spec: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if report_type == "daily":
        if date_spec.get("date") is None:
            issues.append(
                ValidationIssue(code="invalid_date_selection", message="請選擇日報日期。")
            )
        return issues

    if report_type == "weekly":
        start, end = date_spec.get("start"), date_spec.get("end")
        if start is None or end is None:
            issues.append(
                ValidationIssue(
                    code="invalid_date_selection",
                    message="請選擇週報的起迄日期。",
                )
            )
        elif start > end:
            issues.append(
                ValidationIssue(
                    code="invalid_date_selection",
                    message="週報起始日不可晚於結束日。",
                )
            )
        return issues

    if report_type == "monthly":
        if date_spec.get("month") is None:
            issues.append(
                ValidationIssue(
                    code="invalid_date_selection",
                    message="請選擇月報月份。",
                )
            )
        return issues

    issues.append(
        ValidationIssue(
            code="unknown_report_type",
            message=f"未知的報表類型：{report_type}",
        )
    )
    return issues


def is_business_day(value: date) -> bool:
    return value.weekday() < 5
