"""Tests for reconcile key suggestions."""

from __future__ import annotations

from app.services.reconcile_hints import suggest_amount_column, suggest_key_columns


def test_suggest_keys_from_aliases() -> None:
    left = ["交易日期", "帳號", "金額"]
    right = ["交易日期", "帳號", "金額"]
    keys = suggest_key_columns(left, right)
    assert "交易日期" in keys
    assert "帳號" in keys


def test_suggest_amount() -> None:
    assert suggest_amount_column(["金額", "備註"]) == "金額"
