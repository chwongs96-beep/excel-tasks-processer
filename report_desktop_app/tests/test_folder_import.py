"""Tests for folder Excel discovery."""

from __future__ import annotations

import pandas as pd

from app.services.folder_import import list_excel_files


def test_list_excel_files(tmp_path) -> None:
    pd.DataFrame({"a": [1]}).to_excel(tmp_path / "a.xlsx", index=False)
    (tmp_path / "skip.txt").write_text("x", encoding="utf-8")
    paths = list_excel_files(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "a.xlsx"
