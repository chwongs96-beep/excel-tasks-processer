"""Normalize canonical column values — delegates to transformer.py."""

from __future__ import annotations

import pandas as pd

import transformer as tx


def normalize_canonical_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Coerce canonical dtypes; returns warnings list."""
    if frame.empty:
        return frame, []

    warnings: list[str] = []
    out = tx.parse_and_normalize_dates(frame)
    out = tx.convert_numeric_columns(out)
    out = tx.clean_text_columns(out)
    out = tx.derive_amount_if_missing(out)

    if "amount" in frame.columns and frame["amount"].isna().all() and out["amount"].notna().any():
        warnings.append("已依借方/貸方計算 amount 欄位。")

    if "trade_date" in out.columns:
        invalid = int(out["trade_date"].isna().sum())
        if invalid:
            warnings.append(f"有 {invalid} 列 trade_date 無法解析，已保留為空值。")

    return out, warnings
