"""Tests for ValidatorService (shared reporting rules)."""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.core.schemas import DateSpec, LoadedFile
from app.services.validator import ValidatorService


def test_validate_upload_paths_empty() -> None:
    service = ValidatorService()
    messages = service.validate_upload_paths([])
    assert any(m.code == "no_files" for m in messages)
    assert any(m.level == "error" for m in messages)


def test_validate_mapping_empty_is_warning() -> None:
    service = ValidatorService()
    messages = service.validate_mapping({})
    assert len(messages) == 1
    assert messages[0].level == "warning"
    assert messages[0].code == "mapping_empty"


def test_validate_canonical_empty_frame() -> None:
    service = ValidatorService()
    messages = service.validate_canonical_frame(pd.DataFrame())
    assert any(m.code == "empty_dataframe" for m in messages)


def test_validate_date_spec_daily_missing_date() -> None:
    service = ValidatorService()
    spec = DateSpec(report_type="daily", trade_date=None)
    messages = service.validate_date_spec("daily", spec)
    assert messages
