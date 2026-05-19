"""Validate required columns and mapping completeness."""

from __future__ import annotations

import pandas as pd

from reporting.config_loader import load_app_config
from reporting.models import ValidationIssue
from reporting.validation.date_validator import validate_date_columns


def validate_required_columns(
    frame: pd.DataFrame,
    filename: str | None = None,
) -> list[ValidationIssue]:
    cfg = load_app_config()
    issues: list[ValidationIssue] = []
    prefix = f"{filename}: " if filename else ""

    for column in cfg.schema.required_fields:
        if column not in frame.columns:
            issues.append(
                ValidationIssue(
                    code="missing_required_columns",
                    message=f"{prefix}缺少必填欄位「{column}」。",
                    filename=filename,
                    column=column,
                )
            )
            continue
        if frame[column].notna().sum() == 0:
            issues.append(
                ValidationIssue(
                    code="missing_required_columns",
                    message=f"{prefix}必填欄位「{column}」沒有任何有效資料。",
                    filename=filename,
                    column=column,
                )
            )
    return issues


def validate_empty_dataframe(
    frame: pd.DataFrame,
    filename: str | None = None,
) -> list[ValidationIssue]:
    if len(frame) == 0:
        return [
            ValidationIssue(
                code="empty_dataframe",
                message=f"檔案無資料列{f'：{filename}' if filename else ''}。",
                filename=filename,
            )
        ]
    return []


def validate_mapping(
    mapping: dict[str, str],
    required_fields: tuple[str, ...] | None = None,
) -> list[ValidationIssue]:
    cfg = load_app_config()
    required_fields = required_fields or cfg.schema.required_fields
    mapped = set(mapping.values())
    issues: list[ValidationIssue] = []
    for field in required_fields:
        if field not in mapped:
            issues.append(
                ValidationIssue(
                    code="invalid_mapping",
                    message=f"請映射必填欄位：{field}",
                    column=field,
                )
            )
    return issues


def validate_dataframe_content(frame: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_empty_dataframe(frame))
    if issues:
        return issues
    issues.extend(validate_required_columns(frame))
    issues.extend(validate_date_columns(frame))
    return issues
