"""Convert reporting.ValidationIssue to desktop ValidationMessage."""

from __future__ import annotations

from app.core.reporting_bridge import ensure_reporting_package
from app.core.schemas import ValidationMessage

ensure_reporting_package()

from reporting.models import BLOCKING_CODES, ValidationIssue  # noqa: E402


def issue_to_message(issue: ValidationIssue) -> ValidationMessage:
    level = "error" if issue.code in BLOCKING_CODES else "warning"
    if issue.code in {"duplicate_rows"}:
        level = "warning"
    return ValidationMessage(
        level=level,  # type: ignore[arg-type]
        message=issue.message,
        source=issue.filename,
        code=issue.code,
    )


def issues_to_messages(issues: list[ValidationIssue]) -> list[ValidationMessage]:
    return [issue_to_message(i) for i in issues]
