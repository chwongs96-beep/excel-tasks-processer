"""Build progress step labels — no artificial cap on step count."""

from __future__ import annotations

from pathlib import Path

from app.core.range_spec import SourceRangeSpec


def import_file_steps(paths: list[Path]) -> list[str]:
    return [f"讀取 {p.name}" for p in paths] + ["驗證與更新工作階段"]


def consolidate_steps(sources: list[tuple[Path, SourceRangeSpec]]) -> list[str]:
    return (
        ["檢查輸出路徑"]
        + [f"讀取 {path.name}" for path, _ in sources]
        + ["寫入合併 Excel"]
    )


def batch_report_steps(dates: list) -> list[str]:
    from datetime import date

    labels = []
    for d in dates:
        if isinstance(d, date):
            labels.append(f"產報 {d.isoformat()}")
        else:
            labels.append(f"產報 {d}")
    labels.append("整理批次結果")
    return labels


def clear_range_steps() -> list[str]:
    return ["開啟活頁簿", "清除選定範圍", "儲存檔案"]
