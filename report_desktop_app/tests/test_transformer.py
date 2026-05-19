"""Tests for transformation layer."""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.core.schemas import DateSpec
from app.services.transformer import (
    aggregate_for_report_type,
    rename_to_standard_columns,
    resolve_rename_map,
    transform_for_report,
    transform_raw_dataframe,
)


def test_rename_map_from_aliases() -> None:
    mapping = resolve_rename_map(["交易日期", "帳號", "金額"])
    assert mapping["交易日期"] == "trade_date"
    assert mapping["帳號"] == "account_id"
    assert mapping["金額"] == "amount"


def test_transform_raw_normalizes_types() -> None:
    raw = pd.DataFrame(
        {
            "交易日期": ["2024-01-15"],
            "帳號": [" A001 "],
            "金額": ["1,234.5"],
        }
    )
    canonical = transform_raw_dataframe(raw)
    assert "trade_date" in canonical.columns
    assert canonical.loc[0, "account_id"] == "A001"
    assert float(canonical.loc[0, "amount"]) == 1234.5


def test_filter_daily_and_aggregate() -> None:
    canonical = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-15", "2024-01-16"]),
            "account_id": ["A", "A"],
            "symbol": ["X", "X"],
            "description": [None, None],
            "debit": [None, None],
            "credit": [None, None],
            "amount": [100.0, 50.0],
            "currency": ["TWD", "TWD"],
        }
    )
    result = transform_for_report(
        canonical,
        "daily",
        {"date": date(2024, 1, 15)},
    )
    assert not result.blocking
    assert "日報-依帳戶彙總" in result.tables
    summary = result.tables["日報-依帳戶彙總"]
    assert len(summary) == 1
    assert summary["amount"].iloc[0] == 100.0


def test_empty_period_blocks() -> None:
    canonical = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-02-01"]),
            "account_id": ["A"],
            "symbol": ["X"],
            "description": [None],
            "debit": [None],
            "credit": [None],
            "amount": [1.0],
            "currency": ["TWD"],
        }
    )
    result = transform_for_report(
        canonical,
        "daily",
        {"date": date(2024, 1, 1)},
    )
    assert result.blocking
    assert result.tables == {}


def test_service_build_report_tables() -> None:
    from app.services.transformer import TransformerService

    canonical = transform_raw_dataframe(
        pd.DataFrame(
            {
                "date": ["2024-06-01"],
                "account": ["B1"],
                "amount": [10],
            }
        )
    )
    svc = TransformerService()
    out = svc.build_report_tables(
        canonical,
        "monthly",
        DateSpec(report_type="monthly", month=date(2024, 6, 1)),
    )
    assert not out.blocking
    assert len(out.tables) >= 1
