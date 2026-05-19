"""Tests for application controller (no GUI)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.application.app_controller import AppController
from app.core.file_name_filter import FileNameFilter
from app.core.schemas import LoadedFile
from app.core.schemas import DateSpec


def test_clear_session() -> None:
    controller = AppController()
    controller.clear_files()
    assert controller.session.files == []
    assert controller.session.raw_preview.empty


def test_action_validate_requires_files() -> None:
    controller = AppController()
    result = controller.action_validate(
        DateSpec(report_type="daily", trade_date=date.today()),
    )
    assert not result.ok
    assert any(m.level == "error" for m in result.messages)


def test_apply_mapping_preset_to_paths(monkeypatch) -> None:
    controller = AppController()
    loaded = LoadedFile(path=Path("ledger.xlsx"), columns=["交易日期", "帳號", "金額"])
    controller.session.files = [loaded]

    def _fake_load(_name: str) -> dict[str, str]:
        return {
            "x.xlsx:交易日期": "trade_date",
            "x.xlsx:帳號": "account_id",
        }

    monkeypatch.setattr("app.services.mapping_presets.load_preset", _fake_load)
    result = controller.apply_mapping_preset_to_paths("demo", [loaded.path])
    assert result.ok
    assert controller.session.mapping["ledger.xlsx:交易日期"] == "trade_date"
    assert controller.session.mapping["ledger.xlsx:帳號"] == "account_id"


def test_apply_filter_preset(monkeypatch) -> None:
    controller = AppController()
    expected = FileNameFilter(include_any=("成交",), exclude_any=(), case_insensitive=True)
    monkeypatch.setattr("app.services.filter_presets.load_preset", lambda _name: expected)
    result = controller.apply_filter_preset("demo")
    assert result.ok
    assert controller.session.file_name_filter == expected
