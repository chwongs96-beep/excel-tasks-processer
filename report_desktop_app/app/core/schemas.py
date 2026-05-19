"""Data transfer objects and schema definitions for the desktop app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from enum import Enum
from typing import Any, Literal

import pandas as pd

from app.core.range_spec import SourceRangeSpec

ReportType = Literal["daily", "weekly", "monthly"]


class ActionType(str, Enum):
    IMPORT = "import"
    VALIDATE = "validate"
    PREVIEW = "preview"
    GENERATE = "generate"
    CONSOLIDATE = "consolidate"
    RECONCILE = "reconcile"
    BATCH_GENERATE = "batch_generate"


# ---------------------------------------------------------------------------
# Canonical internal schema (loaded from YAML; types defined here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalFieldDef:
    """One column in the unified internal schema."""

    name: str
    dtype: str  # datetime | string | number
    required: bool
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class SchemaConfig:
    """Canonical schema + alias table from canonical_schema.yaml."""

    fields: tuple[CanonicalFieldDef, ...]
    date_columns: tuple[str, ...]
    duplicate_subset: tuple[str, ...]

    @property
    def canonical_fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields if f.required)

    @property
    def column_aliases(self) -> dict[str, tuple[str, ...]]:
        return {f.name: f.aliases for f in self.fields}

    def as_internal_schema_dict(self) -> dict[str, dict[str, Any]]:
        """Human-readable schema summary for docs and debugging."""
        return {
            f.name: {
                "dtype": f.dtype,
                "required": f.required,
                "aliases": list(f.aliases),
            }
            for f in self.fields
        }


@dataclass(frozen=True)
class ReportOutputSpec:
    """One output table in a report (e.g. summary_by_account)."""

    id: str
    title: str
    group_by: tuple[str, ...]
    measures: dict[str, str]  # column -> sum|mean|count


@dataclass(frozen=True)
class ReportDefinition:
    """Aggregation rules for daily / weekly / monthly."""

    report_type: ReportType
    date_mode: str  # single | range | month
    filter_field: str
    outputs: tuple[ReportOutputSpec, ...]
    week_start: str | None = None


@dataclass(frozen=True)
class TableMapping:
    """Where to write one logical table inside an Excel template."""

    sheet: str
    data_start: str  # e.g. A5
    write_header: bool = False
    style_reference_row: int | None = None


@dataclass(frozen=True)
class TemplateSpec:
    """Per-report-type Excel template layout."""

    report_type: ReportType
    file: str
    metadata_cells: dict[str, str]
    table_mappings: dict[str, TableMapping]


@dataclass(frozen=True)
class TemplateConfig:
    """Template mapping loaded from YAML (paths resolved in config.py)."""

    filename_template: str
    templates: dict[str, TemplateSpec]


# ---------------------------------------------------------------------------
# Session / pipeline DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationMessage:
    """User-facing validation entry."""

    level: Literal["error", "warning", "info"]
    message: str
    source: str | None = None
    code: str | None = None


@dataclass
class LoadedFile:
    """Summary of one imported workbook."""

    path: Path
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    sheet_names: list[str] = field(default_factory=list)
    source_range: SourceRangeSpec = field(default_factory=SourceRangeSpec.default)

    def range_summary(self) -> str:
        return self.source_range.summary()


@dataclass
class DateSpec:
    """Report period selection from the UI."""

    report_type: ReportType
    trade_date: date | None = None
    week_start: date | None = None
    week_end: date | None = None
    month: date | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.report_type == "daily":
            return {"date": self.trade_date}
        if self.report_type == "weekly":
            return {"start": self.week_start, "end": self.week_end}
        return {"month": self.month}


@dataclass
class TransformResult:
    """Output of transform + filter + aggregate."""

    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocking: bool = False
    blocking_message: str | None = None


@dataclass
class ReportJob:
    """Input for report generation."""

    files: list[Path]
    mapping: dict[str, str]
    report_type: ReportType
    date_spec: DateSpec
    output_dir: Path | None = None
    template_path: Path | None = None


@dataclass
class ReportOutcome:
    """Result returned to the UI after generation."""

    success: bool
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    output_path: Path | None = None
    filename: str | None = None
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Unified result for UI actions (import, validate, preview, generate)."""

    ok: bool
    action: ActionType | str
    messages: list[ValidationMessage] = field(default_factory=list)
    report_outcome: ReportOutcome | None = None
    detail: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
