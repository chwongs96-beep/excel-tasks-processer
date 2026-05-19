"""Tests for two-file reconciliation."""

from __future__ import annotations

import pandas as pd

from app.core.range_spec import SourceRangeSpec
from app.services.reconcile_service import ReconcileRequest, ReconcileService


def test_reconcile_finds_only_left_and_right(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame(
        {"日期": ["2026-01-01", "2026-01-02"], "金額": [100, 200]}
    ).to_excel(left, index=False)
    pd.DataFrame(
        {"日期": ["2026-01-01", "2026-01-03"], "金額": [100, 300]}
    ).to_excel(right, index=False)

    request = ReconcileRequest(
        left_path=left,
        right_path=right,
        left_range=SourceRangeSpec.default(),
        right_range=SourceRangeSpec.default(),
        key_columns=["日期"],
        amount_column="金額",
    )
    result = ReconcileService().reconcile(request)
    assert result.success
    assert result.summary["僅左邊"] == 1
    assert result.summary["僅右邊"] == 1
    assert result.summary["金額不符"] == 0
