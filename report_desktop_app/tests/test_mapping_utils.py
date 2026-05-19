"""Tests for mapping format conversion and preset remapping."""

from __future__ import annotations

from app.core.mapping_utils import (
    remap_preset_for_file,
    storage_to_ui_mapping,
    ui_to_storage_mapping,
)


def test_ui_storage_roundtrip() -> None:
    ui = {"trade_date": "交易日期", "account_id": "帳號"}
    stored = ui_to_storage_mapping(ui, "ledger.xlsx")
    assert stored == {
        "ledger.xlsx:交易日期": "trade_date",
        "ledger.xlsx:帳號": "account_id",
    }
    assert storage_to_ui_mapping(stored, "ledger.xlsx") == ui


def test_storage_ignores_other_files() -> None:
    stored = {
        "other.xlsx:日期": "trade_date",
        "ledger.xlsx:交易日期": "trade_date",
    }
    ui = storage_to_ui_mapping(stored, "ledger.xlsx")
    assert ui == {"trade_date": "交易日期"}


def test_remap_preset_for_file() -> None:
    preset = {
        "ledger.xlsx:交易日期": "trade_date",
        "ledger.xlsx:帳號": "account_id",
    }
    columns = ["交易日期", "帳號", "金額"]
    stored = remap_preset_for_file(preset, "data.xlsx", columns)
    assert stored == {
        "data.xlsx:交易日期": "trade_date",
        "data.xlsx:帳號": "account_id",
    }


def test_remap_preset_skips_missing_columns() -> None:
    preset = {"ledger.xlsx:不存在": "trade_date"}
    assert remap_preset_for_file(preset, "data.xlsx", ["帳號"]) == {}
