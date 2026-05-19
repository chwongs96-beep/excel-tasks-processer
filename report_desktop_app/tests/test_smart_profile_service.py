"""Tests for smart profile history service."""

from __future__ import annotations

from pathlib import Path

from app.services.smart_profile_service import SmartProfileService


def test_record_and_suggest_by_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "smart_profiles.json"
    svc = SmartProfileService(path)
    cols = ["交易日期", "帳號", "金額"]
    mapping = {"trade_date": "交易日期", "account_id": "帳號"}
    svc.record(filename="brokerA_20260519.xlsx", source_columns=cols, mapping=mapping)

    suggestion = svc.suggest(filename="brokerA_20260520.xlsx", source_columns=cols)
    assert suggestion is not None
    assert suggestion.mapping == mapping
    assert suggestion.confidence >= 0.9


def test_suggest_by_filename_pattern_fallback(tmp_path: Path) -> None:
    path = tmp_path / "smart_profiles.json"
    svc = SmartProfileService(path)
    svc.record(
        filename="tdcc_20260101.xlsx",
        source_columns=["日期", "帳號"],
        mapping={"trade_date": "日期"},
    )

    suggestion = svc.suggest(
        filename="tdcc_20260131.xlsx",
        source_columns=["日期", "帳號", "備註"],
    )
    assert suggestion is not None
    assert suggestion.mapping["trade_date"] == "日期"
    assert suggestion.confidence >= 0.7


def test_suggest_returns_none_when_no_match(tmp_path: Path) -> None:
    path = tmp_path / "smart_profiles.json"
    svc = SmartProfileService(path)
    assert svc.suggest(filename="x.xlsx", source_columns=["A", "B"]) is None
