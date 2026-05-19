"""Safe output path resolution and atomic file writes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from openpyxl import Workbook


class UnsafeOutputPathError(ValueError):
    """Raised when a resolved path would escape the output directory."""


def secure_output_path(output_dir: Path, filename: str) -> Path:
    """
    Resolve ``filename`` under ``output_dir``, rejecting path traversal.

    Only the base name of ``filename`` is used; parent segments are stripped.
    """
    output_dir = output_dir.resolve()
    if ".." in filename or "/" in filename or "\\" in filename:
        raise UnsafeOutputPathError("輸出檔名不可包含路徑分隔符。")
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise UnsafeOutputPathError("輸出檔名無效。")

    candidate = (output_dir / safe_name).resolve()
    try:
        candidate.relative_to(output_dir)
    except ValueError as exc:
        raise UnsafeOutputPathError("輸出路徑必須位於輸出目錄內。") from exc
    return candidate


def atomic_save_workbook(workbook: Workbook, file_path: Path) -> Path:
    """Write workbook atomically via a temp file in the same directory."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        suffix=file_path.suffix,
        dir=file_path.parent,
        prefix=f".{file_path.stem}_",
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        workbook.save(tmp_path)
        tmp_path.replace(file_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return file_path


def atomic_write_bytes(data: bytes, file_path: Path) -> Path:
    """Write raw bytes atomically (fallback workbook export)."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        suffix=file_path.suffix,
        dir=file_path.parent,
        prefix=f".{file_path.stem}_",
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        tmp_path = Path(tmp_name)
        tmp_path.replace(file_path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return file_path
