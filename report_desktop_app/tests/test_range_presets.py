"""Tests for range preset persistence."""

from __future__ import annotations

from app.core.range_spec import SourceRangeSpec
from app.services import range_presets


def test_save_and_load_range_preset(tmp_path, monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config, "RANGE_PRESETS_DIR", tmp_path)
    spec = SourceRangeSpec(sheet="Sheet1", excel_range="B2:H100", header_row=2)
    range_presets.save_preset("broker_a", spec)
    loaded = range_presets.load_preset("broker_a")
    assert loaded.excel_range == "B2:H100"
    assert loaded.header_row == 2
