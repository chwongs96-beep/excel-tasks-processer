"""Tests for Excel range parsing."""

from __future__ import annotations

from app.core.range_spec import SourceRangeSpec, parse_excel_range


def test_parse_excel_range() -> None:
    assert parse_excel_range("B2:H100") == (2, 2, 8, 100)


def test_resolved_bounds_from_range() -> None:
    spec = SourceRangeSpec(excel_range="A1:C3")
    header, min_row, max_row, min_col, max_col = spec.resolved_bounds()
    assert header == 1
    assert min_row == 1 and max_row == 3
    assert min_col == 1 and max_col == 3


def test_range_spec_roundtrip_dict() -> None:
    spec = SourceRangeSpec(sheet="Data", header_row=2, excel_range="B2:F50")
    restored = SourceRangeSpec.from_dict(spec.to_dict())
    assert restored.sheet == spec.sheet
    assert restored.header_row == spec.header_row
    assert restored.excel_range == spec.excel_range
