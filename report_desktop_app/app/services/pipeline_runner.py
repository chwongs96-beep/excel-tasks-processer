"""Run parent ``reporting.pipeline`` for desktop generate (shared load/transform)."""

from __future__ import annotations

from pathlib import Path

from app.core.logger import get_logger
from app.core.reporting_bridge import ensure_reporting_package
from app.core.schemas import ReportJob, ReportOutcome, ValidationMessage
from app.core.validation_convert import issues_to_messages
from app.services.excel_reader import PathUploadAdapter
from app.services.report_generator import ReportGeneratorService

logger = get_logger()


def _pipeline_warnings_to_messages(warnings: list[str]) -> list[ValidationMessage]:
    return [
        ValidationMessage(level="warning", message=text, code="pipeline_warning")
        for text in warnings
    ]


def generate_report_via_pipeline(job: ReportJob) -> ReportOutcome:
    """
    Load, normalize, and aggregate via ``run_report(export=False)``, then export
    with desktop template/output paths.
    """
    ensure_reporting_package()

    from reporting.pipeline import run_report  # noqa: E402

    if not job.files:
        return ReportOutcome(success=False, errors=["請先匯入 Excel 檔案。"])

    uploads = [PathUploadAdapter(Path(p)) for p in job.files]
    logger.info(
        "Pipeline generate: %s, %d file(s)",
        job.report_type,
        len(uploads),
    )

    result = run_report(
        uploads,
        job.mapping,
        job.report_type,
        job.date_spec.to_dict(),
        export=False,
    )

    if not result.tables:
        errors = [i.message for i in result.issues if i.code in _blocking_codes()]
        if not errors and result.issues:
            errors = [result.issues[0].message]
        if not errors:
            errors = ["無法產生報表資料，請檢查映射與日期區間。"]
        return ReportOutcome(
            success=False,
            errors=errors,
            messages=[m.message for m in issues_to_messages(result.issues)]
            + [w for w in result.warnings],
        )

    export_outcome = ReportGeneratorService().export(
        result.tables,
        job.report_type,
        job.date_spec,
        output_dir=job.output_dir,
        template_path=job.template_path,
    )

    extra = _pipeline_warnings_to_messages(result.warnings)
    if extra:
        export_outcome.messages = list(export_outcome.messages) + [
            m.message for m in extra
        ]

    return export_outcome


def _blocking_codes() -> frozenset[str]:
    from reporting.models import BLOCKING_CODES  # noqa: E402

    return BLOCKING_CODES
