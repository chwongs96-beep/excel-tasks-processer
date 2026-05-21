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


def test_reconcile_amount_mismatch_and_tolerance(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A"], "金額": [100.0]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["A"], "金額": [100.05]}).to_excel(right, index=False)

    strict = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            amount_column="金額",
            tolerance=0.01,
        )
    )
    assert strict.success
    assert strict.summary["金額不符"] == 1

    loose = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            amount_column="金額",
            tolerance=0.1,
        )
    )
    assert loose.success
    assert loose.summary["金額不符"] == 0


def test_reconcile_duplicate_keys_warning(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A", "A"], "金額": [1, 2]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["A"], "金額": [1]}).to_excel(right, index=False)

    result = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            amount_column="金額",
        )
    )
    assert result.success
    assert result.summary["左檔重複鍵"] == 1
    assert result.summary["左檔重複列"] == 1
    assert result.warnings
    assert "重複" in result.warnings[0]


def test_reconcile_missing_key_columns(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A"]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["A"]}).to_excel(right, index=False)

    result = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=[],
        )
    )
    assert not result.success
    assert result.errors


def test_reconcile_missing_amount_column(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A"], "金額": [1]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["A"]}).to_excel(right, index=False)

    result = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            amount_column="金額",
        )
    )
    assert not result.success
    assert any("金額" in err for err in result.errors)


def test_reconcile_export_success_and_failure(tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A"], "金額": [1]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["B"], "金額": [2]}).to_excel(right, index=False)

    out = tmp_path / "out" / "diff.xlsx"
    ok = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            output_path=out,
        )
    )
    assert ok.success
    assert ok.output_path is not None
    assert ok.output_path.is_file()

    bad = ReconcileService().reconcile(
        ReconcileRequest(
            left_path=left,
            right_path=right,
            left_range=SourceRangeSpec.default(),
            right_range=SourceRangeSpec.default(),
            key_columns=["日期"],
            output_path=tmp_path,
        )
    )
    assert not bad.success
    assert bad.errors
    assert bad.summary
