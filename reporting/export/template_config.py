"""Load Excel template mapping configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from reporting.config_loader import CONFIG_DIR

TEMPLATE_CONFIG_PATH = CONFIG_DIR / "template_mapping.yaml"
PROJECT_ROOT = CONFIG_DIR.parent


@dataclass
class TableMapping:
    sheet: str
    data_start: str
    write_header: bool = False
    style_reference_row: int | None = None


@dataclass
class TemplateSpec:
    file: str
    metadata_cells: dict[str, str]
    table_mappings: dict[str, TableMapping]


@dataclass
class ExportSettings:
    output_dir: str
    templates_dir: str
    filename_template: str


@dataclass
class TemplateConfig:
    export: ExportSettings
    templates: dict[str, TemplateSpec]
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)

    def template_path(self, report_type: str) -> Path:
        spec = self.templates[report_type]
        return self.project_root / self.export.templates_dir / spec.file

    def output_directory(self) -> Path:
        return self.project_root / self.export.output_dir


def _parse_table_mappings(raw: dict[str, Any]) -> dict[str, TableMapping]:
    mappings: dict[str, TableMapping] = {}
    for key, value in raw.items():
        mappings[key] = TableMapping(
            sheet=value["sheet"],
            data_start=value["data_start"],
            write_header=bool(value.get("write_header", False)),
            style_reference_row=value.get("style_reference_row"),
        )
    return mappings


@lru_cache(maxsize=1)
def load_template_config(path: Path | None = None) -> TemplateConfig:
    config_path = path or TEMPLATE_CONFIG_PATH
    with config_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    export_raw = data.get("export", {})
    export = ExportSettings(
        output_dir=export_raw.get("output_dir", "output"),
        templates_dir=export_raw.get("templates_dir", "templates"),
        filename_template=export_raw.get(
            "filename_template", "{report_type}_{period_label}.xlsx"
        ),
    )

    templates: dict[str, TemplateSpec] = {}
    for report_type, spec in data.get("templates", {}).items():
        templates[report_type] = TemplateSpec(
            file=spec["file"],
            metadata_cells=dict(spec.get("metadata_cells", {})),
            table_mappings=_parse_table_mappings(spec.get("table_mappings", {})),
        )

    return TemplateConfig(export=export, templates=templates)
