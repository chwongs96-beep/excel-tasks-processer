"""Generate multiple period reports in one run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from app.core.logger import get_logger
from app.core.progress import ProgressReporter
from app.core.schemas import DateSpec, ReportJob, ReportType
from app.services.pipeline_runner import generate_report_via_pipeline

logger = get_logger()


@dataclass
class BatchReportRequest:
    report_type: ReportType
    dates: list[date]
    files: list[Path]
    mapping: dict[str, str]
    output_dir: Path
    template_path: Path | None = None


@dataclass
class BatchReportResult:
    success: bool
    generated: list[Path] = field(default_factory=list)
    failed: list[tuple[date, str]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def dates_in_range(
    start: date,
    end: date,
    *,
    business_days_only: bool = False,
) -> list[date]:
    if end < start:
        start, end = end, start
    out: list[date] = []
    current = start
    while current <= end:
        if not business_days_only or current.weekday() < 5:
            out.append(current)
        current += timedelta(days=1)
    return out


class BatchReportService:
    """Run report pipeline once per date (mainly daily)."""

    def run(
        self,
        request: BatchReportRequest,
        progress: ProgressReporter | None = None,
    ) -> BatchReportResult:
        if not request.files:
            return BatchReportResult(success=False, messages=["請先匯入 Excel。"])
        if not request.dates:
            return BatchReportResult(success=False, messages=["請指定至少一個日期。"])
        if request.report_type != "daily":
            return BatchReportResult(
                success=False,
                messages=["批次產報目前僅支援日報；週報／月報請使用單次產生。"],
            )

        generated: list[Path] = []
        failed: list[tuple[date, str]] = []

        for index, trade_date in enumerate(request.dates):
            if progress:
                progress.start(index, f"產報 {trade_date.isoformat()}")
            job = ReportJob(
                files=request.files,
                mapping=request.mapping,
                report_type="daily",
                date_spec=DateSpec(report_type="daily", trade_date=trade_date),
                output_dir=request.output_dir,
                template_path=request.template_path,
            )
            outcome = generate_report_via_pipeline(job)
            if outcome.success and outcome.output_path:
                generated.append(outcome.output_path)
                logger.info("Batch generated %s", outcome.output_path)
                if progress:
                    progress.log(f"  → {outcome.output_path.name}")
            else:
                err = outcome.errors[0] if outcome.errors else "產報失敗"
                failed.append((trade_date, err))
                if progress:
                    progress.log(f"  失敗：{err}")
            if progress:
                progress.done(index)

        summary_index = len(request.dates)
        if progress:
            progress.start(summary_index, "整理批次結果")
            progress.log(f"成功 {len(generated)} 份，失敗 {len(failed)} 份")
            progress.done(summary_index)

        ok = bool(generated) and not failed
        partial = bool(generated) and bool(failed)
        messages = [
            f"成功 {len(generated)} 份",
            f"失敗 {len(failed)} 份" if failed else "",
        ]
        return BatchReportResult(
            success=ok or partial,
            generated=generated,
            failed=failed,
            messages=[m for m in messages if m],
        )
