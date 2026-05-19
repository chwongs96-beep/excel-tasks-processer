"""Domain models for reporting pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

ReportType = Literal["daily", "weekly", "monthly"]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    filename: str | None = None
    column: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


BLOCKING_CODES = frozenset({
    "no_files",
    "too_many_files",
    "duplicate_filename",
    "unsupported_extension",
    "empty_file",
    "read_failed",
    "row_limit_exceeded",
    "empty_dataframe",
    "missing_required_columns",
    "invalid_date_column",
    "invalid_mapping",
    "invalid_date_selection",
    "no_data_in_period",
})


@dataclass
class LoadResult:
    dataframe: pd.DataFrame
    summaries: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    duplicate_count: int = 0

    @property
    def ok(self) -> bool:
        return not any(i.code in BLOCKING_CODES for i in self.issues)

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.code in BLOCKING_CODES]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.code not in BLOCKING_CODES]


@dataclass
class ReportResult:
    tables: dict[str, pd.DataFrame]
    workbook_bytes: bytes | None = None
    filename: str = "report.xlsx"
    file_path: str | None = None
    export_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.code in BLOCKING_CODES for i in self.issues)


MappingSpec = dict[str, str]
