"""Load YAML configuration for schema and report definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass
class FieldDef:
    name: str
    dtype: str
    required: bool
    aliases: list[str]


@dataclass
class SchemaConfig:
    fields: list[FieldDef]
    date_columns: list[str]
    duplicate_subset: list[str]

    @property
    def canonical_fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields if f.required)

    @property
    def column_aliases(self) -> dict[str, tuple[str, ...]]:
        return {f.name: tuple(f.aliases) for f in self.fields}


@dataclass
class OutputDef:
    id: str
    title: str
    group_by: list[str]
    measures: dict[str, str]


@dataclass
class ReportDef:
    date_mode: str
    filter_field: str
    outputs: list[OutputDef]
    week_start: str | None = None


@dataclass
class AppConfig:
    schema: SchemaConfig
    reports: dict[str, ReportDef]
    app_title: str = "證券會計報表自動化"
    max_upload_files: int = 20
    max_rows_per_file: int = 500_000
    allowed_extensions: tuple[str, ...] = (".xlsx", ".xls")
    report_types: tuple[str, ...] = ("daily", "weekly", "monthly")
    report_type_labels: dict[str, str] = field(
        default_factory=lambda: {"daily": "日報", "weekly": "週報", "monthly": "月報"}
    )


def _parse_schema(data: dict[str, Any]) -> SchemaConfig:
    fields = [
        FieldDef(
            name=item["name"],
            dtype=item.get("dtype", "string"),
            required=bool(item.get("required", False)),
            aliases=list(item.get("aliases", [])),
        )
        for item in data.get("fields", [])
    ]
    return SchemaConfig(
        fields=fields,
        date_columns=list(data.get("date_columns", [])),
        duplicate_subset=list(data.get("duplicate_subset", [])),
    )


def _parse_outputs(items: list[dict[str, Any]]) -> list[OutputDef]:
    outputs: list[OutputDef] = []
    for item in items:
        outputs.append(
            OutputDef(
                id=item["id"],
                title=item.get("title", item["id"]),
                group_by=list(item.get("group_by", [])),
                measures=dict(item.get("measures", {})),
            )
        )
    return outputs


def _parse_reports(data: dict[str, Any]) -> dict[str, ReportDef]:
    reports: dict[str, ReportDef] = {}
    for key, value in data.items():
        reports[key] = ReportDef(
            date_mode=value["date_mode"],
            filter_field=value.get("filter_field", "trade_date"),
            week_start=value.get("week_start"),
            outputs=_parse_outputs(value.get("outputs", [])),
        )
    return reports


@lru_cache(maxsize=1)
def load_app_config(config_dir: Path | None = None) -> AppConfig:
    base = config_dir or CONFIG_DIR
    schema_path = base / "canonical_schema.yaml"
    reports_path = base / "report_definitions.yaml"

    with schema_path.open(encoding="utf-8") as fh:
        schema_data = yaml.safe_load(fh)
    with reports_path.open(encoding="utf-8") as fh:
        reports_data = yaml.safe_load(fh)

    return AppConfig(
        schema=_parse_schema(schema_data),
        reports=_parse_reports(reports_data),
    )
