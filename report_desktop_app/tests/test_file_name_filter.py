"""Filename keyword filter for folder import."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.file_name_filter import FileNameFilter
from app.services.folder_import import scan_folder


def test_include_any_requires_match() -> None:
    rules = FileNameFilter(include_any=("成交",), exclude_any=())
    assert rules.matches(Path("broker_成交_2026.xlsx"))
    assert not rules.matches(Path("inventory.xlsx"))


def test_exclude_wins() -> None:
    rules = FileNameFilter(include_any=("成交",), exclude_any=("draft",))
    assert not rules.matches(Path("成交_draft.xlsx"))
    assert rules.matches(Path("成交_final.xlsx"))


def test_empty_include_matches_all_excel_names() -> None:
    rules = FileNameFilter(include_any=(), exclude_any=("temp",))
    assert rules.matches(Path("report.xlsx"))
    assert not rules.matches(Path("report_temp.xlsx"))


def test_scan_folder_filters(tmp_path: Path) -> None:
    (tmp_path / "a_成交.xlsx").write_bytes(b"x")
    (tmp_path / "b_other.xlsx").write_bytes(b"x")
    (tmp_path / "c_成交_draft.xlsx").write_bytes(b"x")

    rules = FileNameFilter(include_any=("成交",), exclude_any=("draft",))
    result = scan_folder(tmp_path, name_filter=rules)
    names = {p.name for p in result.matched}
    assert names == {"a_成交.xlsx"}
    assert len(result.skipped) == 2


def test_filter_roundtrip_dict() -> None:
    rules = FileNameFilter(
        include_any=("A", "B"),
        exclude_any=("x",),
        range_preset="daily_range",
    )
    restored = FileNameFilter.from_dict(rules.to_dict())
    assert restored.include_any == rules.include_any
    assert restored.exclude_any == rules.exclude_any
    assert restored.range_preset == "daily_range"
