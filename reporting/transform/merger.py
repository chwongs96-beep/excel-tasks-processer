"""Merge multiple canonical DataFrames."""

from __future__ import annotations

import pandas as pd

from reporting.config_loader import load_app_config


def merge_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate per-file canonical frames."""
    if not frames:
        cfg = load_app_config()
        return pd.DataFrame(columns=["_source_file", *cfg.schema.canonical_fields])
    return pd.concat(frames, ignore_index=True)


def deduplicate_rows(frame: pd.DataFrame, keep: str = "first") -> pd.DataFrame:
    """Drop duplicate business rows using schema duplicate_subset."""
    cfg = load_app_config()
    subset = [c for c in cfg.schema.duplicate_subset if c in frame.columns]
    if not subset or frame.empty:
        return frame
    return frame.drop_duplicates(subset=subset, keep=keep)
