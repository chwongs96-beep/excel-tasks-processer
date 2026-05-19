"""Tests for transformer.py transformation layer."""

from __future__ import annotations

from datetime import date

import pandas as pd

import config
import transformer as tx


def test_rename_to_standard_columns_adds_optional() -> None:
    raw = pd.DataFrame({"交易日期": ["2026-05-01"], "帳號": ["A1"], "金額": [100]})
    rename = config.build_alias_rename_map(list(raw.columns))
    out = tx.rename_to_standard_columns(raw, rename)
    assert "symbol" in out.columns
    assert pd.isna(out.loc[0, "symbol"])


def test_convert_numeric_with_commas() -> None:
    frame = pd.DataFrame({"amount": ["1,234.5", "200"]})
    out = tx.convert_numeric_columns(frame)
    assert out["amount"].iloc[0] == 1234.5


def test_filter_daily() -> None:
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2026-05-01", "2026-05-02"]),
        "account_id": ["A1", "A2"],
        "amount": [1, 2],
    })
    filtered, issues = tx.filter_by_date_range(
        frame, "daily", {"date": date(2026, 5, 1)}
    )
    assert len(filtered) == 1
    assert not issues


def test_aggregate_daily() -> None:
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2026-05-01", "2026-05-01"]),
        "account_id": ["A1", "A2"],
        "symbol": ["2330", "2317"],
        "description": [None, None],
        "debit": [None, None],
        "credit": [None, None],
        "amount": [1000, 2000],
        "currency": ["TWD", "TWD"],
    })
    tables = tx.aggregate_for_report_type(frame, "daily")
    assert "summary_by_account" in tables
    assert tables["summary_by_account"]["amount"].sum() == 3000


def test_transform_for_report_end_to_end() -> None:
    frame = pd.DataFrame({
        "_source_file": ["f.xlsx"],
        "trade_date": pd.to_datetime(["2026-05-01"]),
        "account_id": ["A1"],
        "symbol": [pd.NA],
        "description": [pd.NA],
        "debit": [pd.NA],
        "credit": [pd.NA],
        "amount": [500],
        "currency": ["TWD"],
    })
    tables, issues, _warnings = tx.transform_for_report(
        frame, "daily", {"date": date(2026, 5, 1)}
    )
    assert not issues
    assert len(tables) >= 1
