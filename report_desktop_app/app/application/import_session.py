"""Mutable state for the current user session."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.core import config
from app.core.file_name_filter import FileNameFilter
from app.core.range_spec import SourceRangeSpec
from app.core.schemas import LoadedFile, ReportType


@dataclass
class ImportSession:
    """Holds imported files and in-memory preview data for one workflow."""

    files: list[LoadedFile] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)
    report_type: ReportType = "daily"
    output_dir: Path = field(default_factory=lambda: config.OUTPUT_DIR)
    template_path: Path = field(default_factory=lambda: config.TEMPLATE_FILES["daily"])
    raw_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    transformed_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    reconcile_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    adjustment: LoadedFile | None = None
    watch_folder: Path | None = None
    watch_recursive: bool = False
    file_name_filter: FileNameFilter = field(default_factory=FileNameFilter.empty)

    @property
    def file_paths(self) -> list[Path]:
        return [item.path for item in self.files]

    def clear(self) -> None:
        self.files.clear()
        self.mapping.clear()
        self.raw_preview = pd.DataFrame()
        self.transformed_preview = pd.DataFrame()
        self.reconcile_preview = pd.DataFrame()
        self.adjustment = None

    def update_file_range(self, path: Path, spec: SourceRangeSpec) -> None:
        for item in self.files:
            if item.path == path:
                item.source_range = spec
                return
