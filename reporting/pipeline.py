"""Single orchestrator: uploads + mapping + report params -> ReportResult."""

from __future__ import annotations

import time
from typing import Any

import report_builder as rb
from reporting.core.filenames import build_output_filename
from reporting.ingestion.file_bundle import load_uploaded_files
from reporting.models import LoadResult, ReportResult, ReportType, ValidationIssue
import transformer as tx
from reporting.transform.normalizer import normalize_canonical_frame
from reporting.validation.column_validator import validate_mapping
from reporting.validation.date_validator import validate_date_selection


def run_report(
    uploaded_files: list[Any],
    mapping: dict[str, str],
    report_type: ReportType,
    date_spec: dict[str, Any],
    *,
    export: bool = True,
    preloaded: LoadResult | None = None,
) -> ReportResult:
    """
    End-to-end reporting pipeline for UI and tests.

    Steps:
        1. Validate uploads and mapping
        2. Load and merge Excel files (skipped when ``preloaded`` is provided)
        3. Normalize canonical values
        4. Filter by report period
        5. Aggregate per report_definitions.yaml
        6. Optionally export to Excel bytes
    """
    started = time.perf_counter()
    issues: list[ValidationIssue] = []

    issues.extend(validate_date_selection(report_type, date_spec))

    if uploaded_files:
        issues.extend(validate_mapping(mapping))

    if preloaded is not None:
        load_result = preloaded
    else:
        load_result = load_uploaded_files(uploaded_files, mapping=mapping or None)
    issues.extend(load_result.issues)

    if not load_result.ok or any(i.code in {"invalid_mapping", "invalid_date_selection"} for i in issues):
        return ReportResult(
            tables={},
            issues=_dedupe_issues(issues),
            warnings=_issue_messages(load_result.warnings),
        )

    canonical, norm_warnings = normalize_canonical_frame(load_result.dataframe)
    tables, transform_issues, transform_warnings = tx.transform_for_report(
        canonical,
        report_type,
        date_spec,
        skip_normalize=True,
    )
    issues.extend(transform_issues)
    warnings = norm_warnings + transform_warnings + _issue_messages(load_result.warnings)

    if not tables and any(i.code == "no_data_in_period" for i in transform_issues):
        return ReportResult(
            tables={},
            issues=_dedupe_issues(issues),
            warnings=warnings,
        )

    file_path: str | None = None
    export_metadata: dict[str, Any] = {}
    workbook_bytes = None
    filename = build_output_filename(report_type, date_spec)

    if export and tables:
        title_map = rb.resolve_title_to_id_map(report_type)
        export_result = rb.build_report_from_template(
            tables,
            report_type,
            date_spec,
            title_to_id=title_map,
        )
        workbook_bytes = export_result.workbook_bytes
        filename = export_result.filename
        file_path = str(export_result.file_path)
        export_metadata = export_result.metadata
        warnings.extend(export_result.warnings)
        issues.extend(export_result.issues)

    elapsed = time.perf_counter() - started
    warnings.append(f"處理完成（{elapsed:.2f} 秒）。")

    return ReportResult(
        tables=tables,
        workbook_bytes=workbook_bytes,
        filename=filename,
        file_path=file_path,
        export_metadata=export_metadata,
        warnings=warnings,
        issues=_dedupe_issues([i for i in issues if i.code not in BLOCKING_OK_WHEN_TABLES]),
    )


BLOCKING_OK_WHEN_TABLES = frozenset({"no_data_in_period"})


def _dedupe_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[str] = set()
    out: list[ValidationIssue] = []
    for issue in issues:
        key = f"{issue.code}:{issue.message}"
        if key not in seen:
            seen.add(key)
            out.append(issue)
    return out


def _issue_messages(issues: list[ValidationIssue]) -> list[str]:
    return [i.message for i in issues]
