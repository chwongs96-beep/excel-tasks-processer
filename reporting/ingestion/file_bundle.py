"""Load and merge multiple uploaded Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from reporting.config_loader import load_app_config
from reporting.ingestion.excel_reader import (
    build_file_summary,
    read_raw_upload,
)
from reporting.mapping.column_mapper import apply_auto_mapping, apply_manual_mapping
from reporting.models import LoadResult, ValidationIssue
from reporting.transform.merger import merge_frames
from reporting.validation.column_validator import validate_dataframe_content
from reporting.validation.date_validator import validate_merged_duplicates
from reporting.validation.file_validator import validate_file_uploads

_READ_BLOCKING = frozenset({
    "unsupported_extension",
    "empty_file",
    "row_limit_exceeded",
    "read_failed",
})


def load_uploaded_files(
    uploaded_files: list[Any],
    mapping: dict[str, str] | None = None,
) -> LoadResult:
    """
    Load uploads, map columns, merge, and validate.

    Args:
        uploaded_files: Streamlit UploadedFile-like objects.
        mapping: Optional manual mapping ``{filename:source_col: canonical}``.
    """
    issues = list(validate_file_uploads(uploaded_files))
    if any(i.code in {"no_files", "too_many_files", "duplicate_filename"} for i in issues):
        return LoadResult(dataframe=_empty_frame(), issues=issues)

    frames: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []

    for uploaded in uploaded_files:
        filename = getattr(uploaded, "name", "upload.xlsx")
        try:
            raw, _, file_issues = read_raw_upload(uploaded)
            issues.extend(file_issues)
            if {i.code for i in file_issues} & _READ_BLOCKING:
                continue
            if raw.empty:
                issues.append(
                    ValidationIssue(
                        code="empty_dataframe",
                        message=f"檔案無資料列：{filename}",
                        filename=filename,
                    )
                )
                continue

            if mapping:
                mapped = apply_manual_mapping(raw, mapping, filename)
            else:
                mapped = apply_auto_mapping(raw)

            mapped.insert(0, "_source_file", filename)
            frames.append(mapped)
            summaries.append(
                build_file_summary(filename, raw, Path(filename).suffix.lower())
            )
        except Exception as exc:  # noqa: BLE001
            issues.append(
                ValidationIssue(
                    code="read_failed",
                    message=f"無法讀取 {filename}：{exc}",
                    filename=filename,
                    details={"error_type": type(exc).__name__},
                )
            )

    if not frames:
        return LoadResult(dataframe=_empty_frame(), summaries=summaries, issues=issues)

    merged = merge_frames(frames)
    issues.extend(validate_dataframe_content(merged))
    dup_issues, duplicate_count = validate_merged_duplicates(merged)
    issues.extend(dup_issues)

    return LoadResult(
        dataframe=merged,
        summaries=summaries,
        issues=issues,
        duplicate_count=duplicate_count,
    )


def _empty_frame() -> pd.DataFrame:
    cfg = load_app_config()
    cols = ["_source_file", *cfg.schema.canonical_fields]
    return pd.DataFrame(columns=cols)
