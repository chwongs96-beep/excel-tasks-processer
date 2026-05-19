"""Map source Excel columns to canonical field names."""

from __future__ import annotations

from typing import Any

import pandas as pd

import config
import transformer as tx


def apply_auto_mapping(frame: pd.DataFrame) -> pd.DataFrame:
    """Map columns using alias table from config.COLUMN_ALIASES."""
    rename_map = build_auto_rename_map(frame.columns)
    return tx.rename_to_standard_columns(frame, rename_map)


def apply_manual_mapping(
    frame: pd.DataFrame,
    mapping: dict[str, str],
    filename: str,
) -> pd.DataFrame:
    """Apply UI mapping keys ``{filename}:{source_column} -> canonical_field``."""
    rename_map = config.build_manual_rename_map(mapping, filename)
    return tx.rename_to_standard_columns(frame, rename_map)


def build_auto_rename_map(columns: Any) -> dict[str, str]:
    return config.build_alias_rename_map([str(c) for c in columns])
