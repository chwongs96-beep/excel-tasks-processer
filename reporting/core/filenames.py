"""Output filename construction from template settings and date selection."""

from __future__ import annotations

from typing import Any

from reporting.core.dates import period_label_for_filename
from reporting.export.template_config import load_template_config
from reporting.models import ReportType


def build_output_filename(
    report_type: ReportType | str,
    date_spec: dict[str, Any],
    *,
    filename_template: str | None = None,
) -> str:
    """
    Build export filename using ``template_mapping.yaml`` export.filename_template.

    Placeholders: ``{report_type}``, ``{period_label}``.
    """
    if filename_template is None:
        filename_template = load_template_config().export.filename_template
    label = period_label_for_filename(report_type, date_spec)  # type: ignore[arg-type]
    return filename_template.format(
        report_type=report_type,
        period_label=label,
    )
