"""Tests for setup preset persistence."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core import config
from app.core.schemas import DateSpec
from app.services import setup_presets
from app.services.setup_presets import SetupPreset


def test_setup_preset_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "SETUP_PRESETS_DIR", tmp_path)
    preset = SetupPreset.from_runtime(
        name="daily_run",
        report_type="daily",
        template_path=Path("C:/tmp/template.xlsx"),
        output_dir=Path("C:/tmp/out"),
        date_spec=DateSpec(report_type="daily", trade_date=date(2026, 5, 19)),
    )
    preset = SetupPreset(
        name=preset.name,
        report_type=preset.report_type,
        template_path=preset.template_path,
        output_dir=preset.output_dir,
        trade_date=preset.trade_date,
        week_start=preset.week_start,
        week_end=preset.week_end,
        month=preset.month,
        mapping_preset="map_a",
        range_preset="range_a",
        filter_preset="filter_a",
    )
    setup_presets.save_preset(preset)
    loaded = setup_presets.load_preset("daily_run")
    assert loaded.name == "daily_run"
    assert loaded.report_type == "daily"
    assert loaded.trade_date == "2026-05-19"
    assert loaded.mapping_preset == "map_a"
    assert loaded.range_preset == "range_a"
    assert loaded.filter_preset == "filter_a"


def test_setup_preset_to_datespec() -> None:
    preset = SetupPreset(
        name="weekly_run",
        report_type="weekly",
        template_path="t.xlsx",
        output_dir="out",
        week_start="2026-05-11",
        week_end="2026-05-15",
    )
    spec = preset.to_date_spec()
    assert spec.report_type == "weekly"
    assert spec.week_start == date(2026, 5, 11)
    assert spec.week_end == date(2026, 5, 15)
