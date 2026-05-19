"""
Application configuration: schema, aliases, and report rules.

Loaded from the ``config/`` **directory** (YAML). Use ``import app_config`` in code;
avoid ``import config`` which is easy to confuse with the ``config/`` folder.
"""

from __future__ import annotations

from typing import Any

from reporting.config_loader import OutputDef, ReportDef, load_app_config

_cfg = load_app_config()

APP_TITLE = _cfg.app_title
REPORT_TYPES = _cfg.report_types
REPORT_TYPE_LABELS = _cfg.report_type_labels
MAX_UPLOAD_FILES = _cfg.max_upload_files
MAX_ROWS_PER_FILE = _cfg.max_rows_per_file
ALLOWED_EXTENSIONS = _cfg.allowed_extensions
OUTPUT_FILENAME_TEMPLATE = "{report_type}_{date_label}.xlsx"

INTERNAL_SCHEMA: dict[str, dict[str, Any]] = {
    field.name: {
        "dtype": field.dtype,
        "required": field.required,
        "aliases": list(field.aliases),
    }
    for field in _cfg.schema.fields
}

CANONICAL_FIELDS: tuple[str, ...] = _cfg.schema.canonical_fields
REQUIRED_CANONICAL_FIELDS: tuple[str, ...] = _cfg.schema.required_fields
OPTIONAL_CANONICAL_FIELDS: tuple[str, ...] = tuple(
    f for f in CANONICAL_FIELDS if f not in REQUIRED_CANONICAL_FIELDS
)

COLUMN_ALIASES: dict[str, tuple[str, ...]] = _cfg.schema.column_aliases
DATE_COLUMNS: tuple[str, ...] = tuple(_cfg.schema.date_columns)
TEXT_COLUMNS: tuple[str, ...] = ("account_id", "symbol", "description", "currency")
NUMERIC_COLUMNS: tuple[str, ...] = ("debit", "credit", "amount")
DUPLICATE_SUBSET: tuple[str, ...] = tuple(_cfg.schema.duplicate_subset)
REPORT_DEFINITIONS: dict[str, ReportDef] = _cfg.reports


def get_report_outputs(report_type: str) -> list[OutputDef]:
    report = REPORT_DEFINITIONS.get(report_type)
    if report is None:
        raise KeyError(f"Unknown report type: {report_type}")
    return report.outputs


def build_alias_rename_map(source_columns: list[str]) -> dict[str, str]:
    from reporting.ingestion.excel_reader import normalize_header

    normalized = {normalize_header(col): col for col in source_columns}
    rename: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_header(alias)
            if key in normalized:
                rename[normalized[key]] = canonical
                break
    return rename


def build_manual_rename_map(
    mapping: dict[str, str],
    filename: str,
) -> dict[str, str]:
    prefix = f"{filename}:"
    rename: dict[str, str] = {}
    for key, canonical in mapping.items():
        if key.startswith(prefix):
            rename[key[len(prefix) :]] = canonical
    return rename


def get_template_config():
    from reporting.export.template_config import load_template_config

    return load_template_config()
