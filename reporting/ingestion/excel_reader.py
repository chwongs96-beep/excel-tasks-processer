"""Read Excel uploads into raw pandas DataFrames."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from reporting.config_loader import load_app_config
from reporting.models import ValidationIssue

_ENGINE_BY_SUFFIX = {".xlsx": "openpyxl", ".xls": "xlrd"}


def read_excel_bytes(data: bytes, suffix: str) -> pd.DataFrame:
    engine = _ENGINE_BY_SUFFIX[suffix]
    buffer: BinaryIO = BytesIO(data)
    return pd.read_excel(buffer, engine=engine, sheet_name=0)


def read_excel_path(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in _ENGINE_BY_SUFFIX:
        raise ValueError(f"Unsupported extension: {suffix}")
    return pd.read_excel(path, engine=_ENGINE_BY_SUFFIX[suffix], sheet_name=0)


def read_upload_bytes(uploaded: Any) -> tuple[bytes, str]:
    filename = getattr(uploaded, "name", "upload.xlsx")
    suffix = Path(filename).suffix.lower()
    if hasattr(uploaded, "getvalue"):
        return uploaded.getvalue(), suffix
    if hasattr(uploaded, "read"):
        uploaded.seek(0)
        return uploaded.read(), suffix
    raise TypeError("Upload object must support read() or getvalue()")


def read_raw_upload(uploaded: Any) -> tuple[pd.DataFrame, str, list[ValidationIssue]]:
    """Return raw dataframe (source headers), filename, and read issues."""
    filename = getattr(uploaded, "name", "upload.xlsx")
    suffix = Path(filename).suffix.lower()
    cfg = load_app_config()
    issues: list[ValidationIssue] = []

    if suffix not in cfg.allowed_extensions:
        issues.append(
            ValidationIssue(
                code="unsupported_extension",
                message=f"不支援的檔案格式：{filename}（僅支援 .xlsx、.xls）",
                filename=filename,
            )
        )
        return pd.DataFrame(), filename, issues

    data, _ = read_upload_bytes(uploaded)
    if len(data) == 0:
        issues.append(
            ValidationIssue(
                code="empty_file",
                message=f"檔案為空：{filename}",
                filename=filename,
            )
        )
        return pd.DataFrame(), filename, issues

    frame = read_excel_bytes(data, suffix)
    if len(frame) > cfg.max_rows_per_file:
        issues.append(
            ValidationIssue(
                code="row_limit_exceeded",
                message=(
                    f"{filename} 列數超過上限"
                    f"（{len(frame):,} > {cfg.max_rows_per_file:,}）"
                ),
                filename=filename,
                details={"row_count": len(frame)},
            )
        )
    return frame, filename, issues


def normalize_header(value: Any) -> str:
    text = str(value).strip().lower()
    return re.sub(r"\s+", "_", text)


def build_file_summary(filename: str, frame: pd.DataFrame, suffix: str) -> dict[str, Any]:
    return {
        "filename": filename,
        "extension": suffix,
        "columns": [str(c) for c in frame.columns],
        "row_count": len(frame),
    }
