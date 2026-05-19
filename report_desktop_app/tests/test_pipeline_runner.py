"""Desktop pipeline bridge uses parent run_report."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from app.core.schemas import DateSpec, ReportJob, ReportOutcome
from app.services.pipeline_runner import generate_report_via_pipeline
from reporting.models import ReportResult


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    path = tmp_path / "ledger.xlsx"
    df = pd.DataFrame({
        "交易日期": ["2026-05-01", "2026-05-02"],
        "帳號": ["A1", "A2"],
        "金額": [100, 200],
    })
    df.to_excel(path, index=False)
    return path


def test_generate_via_pipeline_calls_run_report(sample_xlsx: Path, tmp_path: Path) -> None:
    mapping = {
        f"{sample_xlsx.name}:交易日期": "trade_date",
        f"{sample_xlsx.name}:帳號": "account_id",
        f"{sample_xlsx.name}:金額": "amount",
    }
    job = ReportJob(
        files=[sample_xlsx],
        mapping=mapping,
        report_type="daily",
        date_spec=DateSpec(report_type="daily", trade_date=date(2026, 5, 1)),
        output_dir=tmp_path,
    )

    fake_tables = {"日報-依帳戶彙總": pd.DataFrame({"account_id": ["A1"], "amount": [100]})}
    fake_result = ReportResult(
        tables=fake_tables,
        issues=[],
        warnings=[],
    )

    with patch("reporting.pipeline.run_report", return_value=fake_result) as mock_run:
        with patch(
            "app.services.report_generator.ReportGeneratorService.export",
            return_value=ReportOutcome(
                success=True,
                tables=fake_tables,
                output_path=tmp_path / "daily_2026-05-01.xlsx",
            ),
        ):
            outcome = generate_report_via_pipeline(job)

    assert outcome.success
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs.get("export") is False
