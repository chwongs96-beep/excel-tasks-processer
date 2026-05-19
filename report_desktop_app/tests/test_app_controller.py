"""Tests for application controller (no GUI)."""

from __future__ import annotations

from datetime import date

from app.application.app_controller import AppController
from app.core.schemas import DateSpec


def test_clear_session() -> None:
    controller = AppController()
    controller.clear_files()
    assert controller.session.files == []
    assert controller.session.raw_preview.empty


def test_action_validate_requires_files() -> None:
    controller = AppController()
    result = controller.action_validate(
        DateSpec(report_type="daily", trade_date=date.today()),
    )
    assert not result.ok
    assert any(m.level == "error" for m in result.messages)
