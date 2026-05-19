"""Paths, runtime settings, and YAML-driven schema / report definitions."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core import paths as path_resolver
from app.core.schemas import (
    CanonicalFieldDef,
    ReportDefinition,
    ReportOutputSpec,
    ReportType,
    SchemaConfig,
    TableMapping,
    TemplateConfig,
    TemplateSpec,
)

APP_NAME = "證券會計報表工具"
APP_VERSION = "0.5.0"

DESKTOP_ROOT = path_resolver.resolve_desktop_root()
REPO_ROOT = path_resolver.resolve_repo_root(DESKTOP_ROOT)

APP_DIR = DESKTOP_ROOT / "app"
SHARED_CONFIG_DIR = path_resolver.resolve_shared_config_dir(REPO_ROOT, DESKTOP_ROOT)
CANONICAL_SCHEMA_PATH = SHARED_CONFIG_DIR / "canonical_schema.yaml"
REPORT_DEFINITIONS_PATH = SHARED_CONFIG_DIR / "report_definitions.yaml"
TEMPLATE_MAPPING_PATH = SHARED_CONFIG_DIR / "template_mapping.yaml"
SMART_MODE_PATH = SHARED_CONFIG_DIR / "smart_mode.yaml"
PRESETS_DIR = SHARED_CONFIG_DIR / "mapping_presets"
RANGE_PRESETS_DIR = SHARED_CONFIG_DIR / "range_presets"
FILE_FILTER_PRESETS_DIR = SHARED_CONFIG_DIR / "file_filter_presets"
SETUP_PRESETS_DIR = SHARED_CONFIG_DIR / "setup_presets"

TEMPLATES_DIR = path_resolver.resolve_templates_dir(DESKTOP_ROOT)
OUTPUT_DIR = path_resolver.resolve_output_dir(DESKTOP_ROOT)
LOGS_DIR = path_resolver.resolve_logs_dir(DESKTOP_ROOT)
if path_resolver.is_frozen():
    DATA_DIR = path_resolver.user_data_dir() / "data"
else:
    DATA_DIR = DESKTOP_ROOT / "data"
ASSETS_DIR = APP_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"

TEMPLATE_FILES = {
    "daily": TEMPLATES_DIR / "daily_report_template.xlsx",
    "weekly": TEMPLATES_DIR / "weekly_report_template.xlsx",
    "monthly": TEMPLATES_DIR / "monthly_report_template.xlsx",
}

ALLOWED_EXTENSIONS = frozenset({".xlsx", ".xls"})
MAX_FILES = int(os.environ.get("REPORT_MAX_FILES", "20"))
PREVIEW_ROW_LIMIT = int(os.environ.get("REPORT_PREVIEW_ROWS", "500"))
DIALOG_PREVIEW_ROWS = int(os.environ.get("REPORT_DIALOG_PREVIEW_ROWS", "25"))
MAX_ROWS_PER_FILE = int(os.environ.get("REPORT_MAX_ROWS", "500000"))

SCHEMA: SchemaConfig
REPORT_DEFINITIONS: dict[ReportType, ReportDefinition]
CANONICAL_FIELDS: tuple[str, ...]
REQUIRED_CANONICAL_FIELDS: tuple[str, ...]
COLUMN_ALIASES: dict[str, tuple[str, ...]]
DATE_COLUMNS: tuple[str, ...]
TEXT_COLUMNS: tuple[str, ...] = ("account_id", "symbol", "description", "currency")
NUMERIC_COLUMNS: tuple[str, ...] = ("debit", "credit", "amount")
DUPLICATE_SUBSET: tuple[str, ...]


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RANGE_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    FILE_FILTER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)


def normalize_header(value: Any) -> str:
    text = str(value).strip().lower()
    return re.sub(r"\s+", "_", text)


def build_alias_rename_map(source_columns: list[str]) -> dict[str, str]:
    normalized = {normalize_header(col): col for col in source_columns}
    rename: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_header(alias)
            if key in normalized:
                rename[normalized[key]] = canonical
                break
    return rename


def build_manual_rename_map(mapping: dict[str, str], filename: str) -> dict[str, str]:
    prefix = f"{filename}:"
    rename: dict[str, str] = {}
    for key, canonical in mapping.items():
        if key.startswith(prefix):
            source_col = key[len(prefix) :]
            if source_col and canonical:
                rename[source_col] = canonical
    return rename


def get_report_definition(report_type: ReportType) -> ReportDefinition:
    if report_type not in REPORT_DEFINITIONS:
        raise KeyError(f"Unknown report type: {report_type}")
    return REPORT_DEFINITIONS[report_type]


def title_to_output_id_map(report_type: ReportType) -> dict[str, str]:
    report_def = get_report_definition(report_type)
    return {output.title: output.id for output in report_def.outputs}


def _parse_schema(data: dict[str, Any]) -> SchemaConfig:
    fields = tuple(
        CanonicalFieldDef(
            name=item["name"],
            dtype=item.get("dtype", "string"),
            required=bool(item.get("required", False)),
            aliases=tuple(item.get("aliases", [])),
        )
        for item in data.get("fields", [])
    )
    return SchemaConfig(
        fields=fields,
        date_columns=tuple(data.get("date_columns", [])),
        duplicate_subset=tuple(data.get("duplicate_subset", [])),
    )


def _parse_outputs(items: list[dict[str, Any]]) -> tuple[ReportOutputSpec, ...]:
    return tuple(
        ReportOutputSpec(
            id=item["id"],
            title=item.get("title", item["id"]),
            group_by=tuple(item.get("group_by", [])),
            measures=dict(item.get("measures", {})),
        )
        for item in items
    )


def _parse_reports(data: dict[str, Any]) -> dict[ReportType, ReportDefinition]:
    reports: dict[ReportType, ReportDefinition] = {}
    for key, item in data.items():
        if key not in ("daily", "weekly", "monthly"):
            continue
        reports[key] = ReportDefinition(  # type: ignore[literal-required]
            report_type=key,
            date_mode=item.get("date_mode", "single"),
            filter_field=item.get("filter_field", "trade_date"),
            outputs=_parse_outputs(item.get("outputs", [])),
            week_start=item.get("week_start"),
        )
    return reports


@lru_cache(maxsize=1)
def load_schema_config() -> SchemaConfig:
    if not CANONICAL_SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"找不到 schema 設定：{CANONICAL_SCHEMA_PATH}")
    with CANONICAL_SCHEMA_PATH.open(encoding="utf-8") as handle:
        return _parse_schema(yaml.safe_load(handle) or {})


@lru_cache(maxsize=1)
def load_report_definitions() -> dict[ReportType, ReportDefinition]:
    if not REPORT_DEFINITIONS_PATH.is_file():
        raise FileNotFoundError(f"找不到報表定義：{REPORT_DEFINITIONS_PATH}")
    with REPORT_DEFINITIONS_PATH.open(encoding="utf-8") as handle:
        return _parse_reports(yaml.safe_load(handle) or {})


def _parse_table_mappings(raw: dict[str, Any]) -> dict[str, TableMapping]:
    return {
        key: TableMapping(
            sheet=value["sheet"],
            data_start=value["data_start"],
            write_header=bool(value.get("write_header", False)),
            style_reference_row=value.get("style_reference_row"),
        )
        for key, value in raw.items()
    }


@lru_cache(maxsize=1)
def load_template_config() -> TemplateConfig:
    if not TEMPLATE_MAPPING_PATH.is_file():
        raise FileNotFoundError(f"找不到範本映射設定：{TEMPLATE_MAPPING_PATH}")
    with TEMPLATE_MAPPING_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    export_raw = data.get("export", {})
    filename_template = export_raw.get(
        "filename_template",
        "{report_type}_{period_label}.xlsx",
    )

    templates: dict[str, TemplateSpec] = {}
    for report_type, spec in data.get("templates", {}).items():
        if report_type not in TEMPLATE_FILES:
            continue
        templates[report_type] = TemplateSpec(
            report_type=report_type,  # type: ignore[arg-type]
            file=TEMPLATE_FILES[report_type].name,
            metadata_cells=dict(spec.get("metadata_cells", {})),
            table_mappings=_parse_table_mappings(spec.get("table_mappings", {})),
        )

    return TemplateConfig(
        filename_template=filename_template,
        templates=templates,
    )


@lru_cache(maxsize=1)
def load_smart_mode_config() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": True,
        "advisor": {
            "auto_apply_threshold": 0.85,
            "suggest_threshold": 0.60,
        },
    }
    if not SMART_MODE_PATH.is_file():
        return defaults
    with SMART_MODE_PATH.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        return defaults
    advisor = loaded.get("advisor", {})
    if not isinstance(advisor, dict):
        advisor = {}
    return {
        "enabled": bool(loaded.get("enabled", defaults["enabled"])),
        "advisor": {
            "auto_apply_threshold": advisor.get(
                "auto_apply_threshold",
                defaults["advisor"]["auto_apply_threshold"],
            ),
            "suggest_threshold": advisor.get(
                "suggest_threshold",
                defaults["advisor"]["suggest_threshold"],
            ),
        },
    }


def resolve_template_path(report_type: ReportType) -> Path:
    return TEMPLATE_FILES[report_type]


def _init_module_constants() -> None:
    global SCHEMA, REPORT_DEFINITIONS  # noqa: PLW0603
    global CANONICAL_FIELDS, REQUIRED_CANONICAL_FIELDS  # noqa: PLW0603
    global COLUMN_ALIASES, DATE_COLUMNS, DUPLICATE_SUBSET  # noqa: PLW0603

    SCHEMA = load_schema_config()
    REPORT_DEFINITIONS = load_report_definitions()
    CANONICAL_FIELDS = SCHEMA.canonical_fields
    REQUIRED_CANONICAL_FIELDS = SCHEMA.required_fields
    COLUMN_ALIASES = SCHEMA.column_aliases
    DATE_COLUMNS = SCHEMA.date_columns
    DUPLICATE_SUBSET = SCHEMA.duplicate_subset


_init_module_constants()
