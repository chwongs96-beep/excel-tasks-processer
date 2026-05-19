"""Tests for column mapping."""

from __future__ import annotations

import pandas as pd

from reporting.mapping.column_mapper import apply_auto_mapping, apply_manual_mapping
from reporting.mapping.presets import list_presets, load_preset, save_preset


def test_auto_mapping_chinese_headers() -> None:
    frame = pd.DataFrame({
        "交易日期": ["2026-05-01"],
        "帳號": ["A001"],
        "金額": [100],
    })
    mapped = apply_auto_mapping(frame)
    assert list(mapped.columns) == [
        "trade_date", "account_id", "symbol", "description",
        "debit", "credit", "amount", "currency",
    ]
    assert mapped.loc[0, "account_id"] == "A001"


def test_manual_mapping() -> None:
    frame = pd.DataFrame({"D": ["2026-05-01"], "Acct": ["A1"], "Amt": [10]})
    mapping = {
        "f.xlsx:D": "trade_date",
        "f.xlsx:Acct": "account_id",
        "f.xlsx:Amt": "amount",
    }
    mapped = apply_manual_mapping(frame, mapping, "f.xlsx")
    assert mapped["amount"].iloc[0] == 10


def test_preset_roundtrip(tmp_path, monkeypatch) -> None:
    import reporting.mapping.presets as presets

    monkeypatch.setattr(presets, "PRESETS_DIR", tmp_path)
    save_preset("test", {"a.xlsx:日期": "trade_date"})
    assert "test" in list_presets()
    assert load_preset("test")["a.xlsx:日期"] == "trade_date"
