"""Input validation — delegates to shared reporting.validation rules."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core import config
from app.core.reporting_bridge import ensure_reporting_package
from app.core.schemas import DateSpec, LoadedFile, ReportType, ValidationMessage
from app.core.validation_convert import issues_to_messages
from app.services.excel_reader import PathUploadAdapter

ensure_reporting_package()

from reporting.validation.column_validator import (  # noqa: E402
    validate_dataframe_content,
    validate_mapping,
)
from reporting.validation.date_validator import validate_date_selection  # noqa: E402
from reporting.validation.file_validator import validate_file_uploads  # noqa: E402


class ValidatorService:
    """Validate files, mappings, canonical data, and report parameters."""

    def validate_upload_paths(self, files: list[LoadedFile]) -> list[ValidationMessage]:
        uploads = [PathUploadAdapter(f.path) for f in files]
        return issues_to_messages(validate_file_uploads(uploads))

    def validate_mapping(self, mapping: dict[str, str]) -> list[ValidationMessage]:
        if not mapping:
            return [
                ValidationMessage(
                    level="warning",
                    message="尚未手動設定欄位映射，將嘗試依欄位別名自動對應。",
                    source="mapping",
                    code="mapping_empty",
                )
            ]
        return issues_to_messages(validate_mapping(mapping))

    def validate_canonical_frame(
        self,
        frame: pd.DataFrame,
        *,
        filename: str | None = None,
    ) -> list[ValidationMessage]:
        if frame.empty:
            return [
                ValidationMessage(
                    level="error",
                    message="合併後沒有資料列，請確認 Excel 內容與欄位映射。",
                    code="empty_dataframe",
                )
            ]
        return issues_to_messages(validate_dataframe_content(frame))

    def validate_date_spec(
        self,
        report_type: ReportType,
        date_spec: DateSpec,
    ) -> list[ValidationMessage]:
        return issues_to_messages(
            validate_date_selection(report_type, date_spec.to_dict())
        )

    def validate_for_report(
        self,
        files: list[LoadedFile],
        mapping: dict[str, str],
        canonical: pd.DataFrame,
        date_spec: DateSpec,
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        messages.extend(self.validate_upload_paths(files))
        messages.extend(self.validate_mapping(mapping))
        messages.extend(self.validate_canonical_frame(canonical))
        messages.extend(self.validate_date_spec(date_spec.report_type, date_spec))
        return messages
