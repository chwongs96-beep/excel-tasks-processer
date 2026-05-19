"""Tests for multi-file Excel consolidation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.range_spec import SourceRangeSpec
from app.services.consolidation_service import ConsolidateRequest, ConsolidationService

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_ledger.xlsx"


@pytest.fixture
def sample_path() -> Path:
    if not FIXTURE.is_file():
        pytest.skip("sample_ledger.xlsx missing")
    return FIXTURE


def test_consolidate_single_sheet(tmp_path: Path, sample_path: Path) -> None:
    out = tmp_path / "merged.xlsx"
    request = ConsolidateRequest(
        sources=[(sample_path, SourceRangeSpec.default())],
        output_path=out,
        merge_mode="single_sheet",
    )
    result = ConsolidationService().consolidate(request)
    assert result.success
    assert result.output_path is not None
    assert result.output_path.is_file()
    assert result.row_counts.get("合併資料", 0) > 0
