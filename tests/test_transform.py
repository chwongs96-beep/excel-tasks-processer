"""Tests for transform layer."""

from __future__ import annotations

from datetime import date

import pandas as pd

from reporting.transform.filters import filter_by_report_period
from reporting.transform.merger import deduplicate_rows, merge_frames
from reporting.transform.normalizer import normalize_canonical_frame


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "_source_file": ["a.xlsx", "a.xlsx", "a.xlsx"],
        "trade_date": pd.to_datetime(["2026-05-01", "2026-05-02", "2026-05-10"]),
        "account_id": ["A1", "A1", "A2"],
        "symbol": ["2330", "2330", "2317"],
        "description": [None, None, None],
        "debit": [None, None, None],
        "credit": [None, None, None],
        "amount": [100, 200, 300],
        "currency": ["TWD", "TWD", "TWD"],
    })


def test_merge_frames() -> None:
    f1 = _sample_frame()
    f2 = f1.copy()
    f2["_source_file"] = "b.xlsx"
    merged = merge_frames([f1, f2])
    assert len(merged) == 6


def test_deduplicate() -> None:
    frame = _sample_frame()
    dup = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    deduped = deduplicate_rows(dup)
    assert len(deduped) == len(frame)


def test_filter_daily() -> None:
    frame = _sample_frame()
    filtered, issues = filter_by_report_period(
        frame, "daily", {"date": date(2026, 5, 1)}
    )
    assert len(filtered) == 1
    assert not issues


def test_normalize_amount_from_debit_credit() -> None:
    frame = pd.DataFrame({
        "_source_file": ["a.xlsx"],
        "trade_date": pd.to_datetime(["2026-05-01"]),
        "account_id": ["A1"],
        "symbol": [pd.NA],
        "description": [pd.NA],
        "debit": [150],
        "credit": [50],
        "amount": [pd.NA],
        "currency": ["TWD"],
    })
    normalized, warnings = normalize_canonical_frame(frame)
    assert normalized["amount"].iloc[0] == 100
    assert warnings
