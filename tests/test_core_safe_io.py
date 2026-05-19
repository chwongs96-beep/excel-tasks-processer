"""Tests for secure output paths and atomic writes."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from reporting.core.safe_io import (
    UnsafeOutputPathError,
    atomic_save_workbook,
    secure_output_path,
)


def test_secure_output_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(UnsafeOutputPathError):
        secure_output_path(tmp_path, "../../etc/passwd.xlsx")


def test_secure_output_path_rejects_nested_name(tmp_path: Path) -> None:
    with pytest.raises(UnsafeOutputPathError):
        secure_output_path(tmp_path, "nested/report.xlsx")


def test_secure_output_path_accepts_simple_name(tmp_path: Path) -> None:
    resolved = secure_output_path(tmp_path, "daily_2026-05-01.xlsx")
    assert resolved == tmp_path / "daily_2026-05-01.xlsx"


def test_atomic_save_workbook(tmp_path: Path) -> None:
    target = tmp_path / "out.xlsx"
    wb = Workbook()
    wb.active["A1"] = "ok"
    atomic_save_workbook(wb, target)
    assert target.is_file()
    wb.close()
