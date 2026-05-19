"""Tests for report aggregation."""

from __future__ import annotations

from datetime import date

import pandas as pd

from reporting.aggregation.daily import aggregate_daily
from reporting.pipeline import run_report
from tests.conftest import FakeUpload


def _canonical_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "_source_file": ["a.xlsx", "a.xlsx"],
        "trade_date": pd.to_datetime(["2026-05-01", "2026-05-01"]),
        "account_id": ["A1", "A2"],
        "symbol": ["2330", "2317"],
        "description": [None, None],
        "debit": [None, None],
        "credit": [None, None],
        "amount": [1000, 2500],
        "currency": ["TWD", "TWD"],
    })


def test_aggregate_daily_summary() -> None:
    tables = aggregate_daily(_canonical_frame())
    summary = tables["summary_by_account"]
    assert len(summary) == 2
    assert summary["amount"].sum() == 3500


def test_pipeline_daily(xlsx_upload: FakeUpload) -> None:
    mapping = {
        "ledger.xlsx:交易日期": "trade_date",
        "ledger.xlsx:帳號": "account_id",
        "ledger.xlsx:金額": "amount",
    }
    result = run_report(
        [xlsx_upload],
        mapping,
        "daily",
        {"date": date(2026, 5, 1)},
    )
    assert result.ok
    assert result.workbook_bytes
    assert len(result.tables) >= 1
