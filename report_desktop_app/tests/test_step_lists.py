"""Progress step list builders — no step count cap."""

from __future__ import annotations

from pathlib import Path

from app.core.range_spec import SourceRangeSpec
from app.ui.step_lists import consolidate_steps, import_file_steps


def test_import_steps_scale_with_file_count() -> None:
    paths = [Path(f"f{i}.xlsx") for i in range(12)]
    steps = import_file_steps(paths)
    assert len(steps) == 13
    assert steps[0] == "讀取 f0.xlsx"
    assert steps[-1] == "驗證與更新工作階段"


def test_consolidate_steps_scale_with_sources() -> None:
    sources = [(Path(f"a{i}.xlsx"), SourceRangeSpec()) for i in range(10)]
    steps = consolidate_steps(sources)
    assert len(steps) == 12
    assert steps[0] == "檢查輸出路徑"
    assert steps[-1] == "寫入合併 Excel"
