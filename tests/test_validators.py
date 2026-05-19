"""Legacy test module — delegates to reporting package."""

from __future__ import annotations

from datetime import date

import pandas as pd

from reporting.ingestion.excel_reader import read_excel_bytes
from reporting.ingestion.file_bundle import load_uploaded_files
from reporting.mapping.column_mapper import apply_auto_mapping
from reporting.models import ValidationIssue
from reporting.validation.date_validator import (
    is_business_day,
    parse_dates,
    validate_date_columns,
    validate_date_selection,
    validate_merged_duplicates,
)
from reporting.validation.column_validator import (
    validate_dataframe_content,
    validate_required_columns,
)
from reporting.validation.file_validator import validate_file_uploads
from tests.conftest import FakeUpload


def test_validate_file_uploads_requires_files() -> None:
    assert any(i.code == "no_files" for i in validate_file_uploads([]))


def test_validate_file_uploads_rejects_bad_extension() -> None:
    assert any(
        i.code == "unsupported_extension"
        for i in validate_file_uploads([FakeUpload("data.csv", b"abc")])
    )


def test_validate_file_uploads_rejects_duplicate_names(xlsx_bytes: bytes) -> None:
    uploads = [FakeUpload("same.xlsx", xlsx_bytes), FakeUpload("same.xlsx", xlsx_bytes)]
    assert any(i.code == "duplicate_filename" for i in validate_file_uploads(uploads))


def test_validate_required_columns_missing() -> None:
    frame = pd.DataFrame({"account_id": ["A1"], "amount": [1]})
    assert any(
        i.code == "missing_required_columns" and i.column == "trade_date"
        for i in validate_required_columns(frame)
    )


def test_validate_empty_dataframe_via_content() -> None:
    from reporting.validation.column_validator import validate_empty_dataframe

    assert any(i.code == "empty_dataframe" for i in validate_empty_dataframe(pd.DataFrame()))


def test_validate_date_columns_invalid(invalid_date_xlsx_bytes: bytes) -> None:
    raw = read_excel_bytes(invalid_date_xlsx_bytes, ".xlsx")
    frame = apply_auto_mapping(raw)
    assert any(i.code == "invalid_date_column" for i in validate_date_columns(frame))


def test_parse_dates_accepts_strings() -> None:
    assert parse_dates(pd.Series(["2026-05-01", "2026-05-02"])).notna().all()


def test_validate_merged_duplicates_warning() -> None:
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2026-05-01", "2026-05-01"]),
        "account_id": ["A1", "A1"],
        "symbol": ["2330", "2330"],
        "amount": [100, 100],
        "_source_file": ["f1.xlsx", "f1.xlsx"],
    })
    issues, count = validate_merged_duplicates(frame)
    assert count == 2
    assert any(i.code == "duplicate_rows" for i in issues)


def test_validate_date_selection_weekly_inverted() -> None:
    issues = validate_date_selection(
        "weekly",
        {"start": date(2026, 5, 10), "end": date(2026, 5, 1)},
    )
    assert any(i.code == "invalid_date_selection" for i in issues)


def test_is_business_day() -> None:
    assert is_business_day(date(2026, 5, 16)) is False
    assert is_business_day(date(2026, 5, 18)) is True


def test_load_uploaded_files_success(xlsx_upload: FakeUpload) -> None:
    result = load_uploaded_files([xlsx_upload])
    assert result.ok
    assert len(result.dataframe) == 2


def test_load_uploaded_files_empty_content(empty_xlsx_bytes: bytes) -> None:
    result = load_uploaded_files([FakeUpload("empty.xlsx", empty_xlsx_bytes)])
    assert not result.ok
    assert any(i.code == "empty_dataframe" for i in result.blocking_issues)


def test_validate_dataframe_content_ok(xlsx_bytes: bytes) -> None:
    raw = read_excel_bytes(xlsx_bytes, ".xlsx")
    frame = apply_auto_mapping(raw)
    assert validate_dataframe_content(frame) == []


def test_merge_multiple_files(xlsx_bytes: bytes) -> None:
    result = load_uploaded_files([
        FakeUpload("a.xlsx", xlsx_bytes),
        FakeUpload("b.xlsx", xlsx_bytes),
    ])
    assert result.ok
    assert len(result.dataframe) == 4


def test_issues_are_structured() -> None:
    assert ValidationIssue(code="no_files", message="test").to_dict()["code"] == "no_files"


def test_validate_mapping_requires_required_fields() -> None:
    from reporting.validation.column_validator import validate_mapping

    issues = validate_mapping({})
    assert any(i.code == "invalid_mapping" for i in issues)
