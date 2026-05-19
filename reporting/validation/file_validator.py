"""Validate uploaded file metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reporting.config_loader import load_app_config
from reporting.models import ValidationIssue


def validate_file_uploads(uploaded_files: list[Any]) -> list[ValidationIssue]:
    cfg = load_app_config()
    issues: list[ValidationIssue] = []

    if not uploaded_files:
        issues.append(
            ValidationIssue(
                code="no_files",
                message="請至少上傳一個 Excel 檔案（.xlsx 或 .xls）。",
            )
        )
        return issues

    if len(uploaded_files) > cfg.max_upload_files:
        issues.append(
            ValidationIssue(
                code="too_many_files",
                message=f"上傳檔案數量超過上限（最多 {cfg.max_upload_files} 個）。",
                details={"count": len(uploaded_files)},
            )
        )

    names = [getattr(f, "name", "") for f in uploaded_files]
    if len(names) != len(set(names)):
        issues.append(
            ValidationIssue(
                code="duplicate_filename",
                message="偵測到重複的檔案名稱，請移除重複項目後再試。",
            )
        )

    for uploaded in uploaded_files:
        name = getattr(uploaded, "name", "")
        suffix = Path(name).suffix.lower()
        if suffix not in cfg.allowed_extensions:
            issues.append(
                ValidationIssue(
                    code="unsupported_extension",
                    message=f"不支援的檔案格式：{name}（僅支援 .xlsx、.xls）",
                    filename=name,
                )
            )
        size = getattr(uploaded, "size", None)
        if size is not None and size == 0:
            issues.append(
                ValidationIssue(
                    code="empty_file",
                    message=f"檔案為空：{name}",
                    filename=name,
                )
            )

    return issues
