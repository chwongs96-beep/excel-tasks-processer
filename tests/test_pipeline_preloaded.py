"""Pipeline should reuse preloaded LoadResult without re-reading files."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pandas as pd

from reporting.models import LoadResult
from reporting.pipeline import run_report


class _FakeUpload:
    name = "t.xlsx"
    size = 1


def test_run_report_uses_preloaded_frame() -> None:
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2026-05-01"]),
        "account_id": ["A1"],
        "symbol": [pd.NA],
        "description": [pd.NA],
        "debit": [pd.NA],
        "credit": [pd.NA],
        "amount": [100.0],
        "currency": ["TWD"],
        "_source_file": ["t.xlsx"],
    })
    preloaded = LoadResult(dataframe=frame, issues=[])

    mapping = {
        "t.xlsx:trade_date": "trade_date",
        "t.xlsx:account_id": "account_id",
        "t.xlsx:amount": "amount",
    }
    with patch(
        "reporting.pipeline.load_uploaded_files",
        side_effect=AssertionError("should not reload"),
    ):
        result = run_report(
            [_FakeUpload()],
            mapping,
            "daily",
            {"date": date(2026, 5, 1)},
            export=False,
            preloaded=preloaded,
        )

    assert result.tables or result.issues
