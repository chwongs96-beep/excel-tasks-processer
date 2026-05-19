"""Ensure pipeline skips duplicate normalization in transform_for_report."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pandas as pd

import transformer as tx


def test_transform_for_report_skip_normalize() -> None:
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2026-05-01"]),
        "account_id": ["A1"],
        "amount": [100.0],
    })
    with patch.object(tx, "parse_and_normalize_dates") as mock_dates:
        tx.transform_for_report(
            frame,
            "daily",
            {"date": date(2026, 5, 1)},
            skip_normalize=True,
        )
        mock_dates.assert_not_called()
