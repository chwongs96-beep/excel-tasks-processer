"""Discover Excel files under a folder (manual batch import)."""

from __future__ import annotations

from pathlib import Path

from app.core import config
from app.core.file_name_filter import FileNameFilter, FolderScanResult


def list_excel_files(
    folder: Path,
    *,
    recursive: bool = False,
    name_filter: FileNameFilter | None = None,
) -> list[Path]:
    """Return Excel paths under ``folder``, optionally filtered by filename rules."""
    return scan_folder(folder, recursive=recursive, name_filter=name_filter).matched


def scan_folder(
    folder: Path,
    *,
    recursive: bool = False,
    name_filter: FileNameFilter | None = None,
) -> FolderScanResult:
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"不是有效的資料夾：{folder}")

    rules = name_filter or FileNameFilter.empty()
    pattern = "**/*" if recursive else "*"
    matched: list[Path] = []
    skipped: list[Path] = []

    for path in sorted(folder.glob(pattern)):
        if not path.is_file():
            continue
        if path.suffix.lower() not in config.ALLOWED_EXTENSIONS:
            continue
        resolved = path.resolve()
        if rules.matches(resolved):
            matched.append(resolved)
        else:
            skipped.append(resolved)

    return FolderScanResult(folder=folder.resolve(), matched=matched, skipped=skipped)
