"""Tests for application controller (no GUI)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.application.app_controller import AppController
from app.core.file_name_filter import FileNameFilter
from app.core.range_spec import SourceRangeSpec
from app.core.schemas import LoadedFile
from app.core.schemas import DateSpec
from app.services.reconcile_service import ReconcileRequest, ReconcileResult


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


def test_apply_mapping_preset_to_paths(monkeypatch) -> None:
    controller = AppController()
    loaded = LoadedFile(path=Path("ledger.xlsx"), columns=["交易日期", "帳號", "金額"])
    controller.session.files = [loaded]

    def _fake_load(_name: str) -> dict[str, str]:
        return {
            "x.xlsx:交易日期": "trade_date",
            "x.xlsx:帳號": "account_id",
        }

    monkeypatch.setattr("app.services.mapping_presets.load_preset", _fake_load)
    result = controller.apply_mapping_preset_to_paths("demo", [loaded.path])
    assert result.ok
    assert controller.session.mapping["ledger.xlsx:交易日期"] == "trade_date"
    assert controller.session.mapping["ledger.xlsx:帳號"] == "account_id"


def test_apply_filter_preset(monkeypatch) -> None:
    controller = AppController()
    expected = FileNameFilter(include_any=("成交",), exclude_any=(), case_insensitive=True)
    monkeypatch.setattr("app.services.filter_presets.load_preset", lambda _name: expected)
    result = controller.apply_filter_preset("demo")
    assert result.ok
    assert controller.session.file_name_filter == expected


def test_format_reconcile_summary_includes_duplicate_keys() -> None:
    text = AppController.format_reconcile_summary(
        {"僅左邊": 2, "僅右邊": 1, "鍵相符": 5, "金額不符": 0, "左檔重複鍵": 1, "右檔重複鍵": 0}
    )
    assert "僅左邊 2" in text
    assert "重複鍵" in text


def test_action_reconcile_messages_consistent(monkeypatch, tmp_path) -> None:
    controller = AppController()
    fake = ReconcileResult(
        success=True,
        summary={
            "僅左邊": 1,
            "僅右邊": 2,
            "鍵相符": 3,
            "金額不符": 4,
            "左檔重複鍵": 1,
            "右檔重複鍵": 0,
        },
        warnings=["重複鍵警告"],
    )

    monkeypatch.setattr(controller._reconcile, "reconcile", lambda _req: fake)
    request = ReconcileRequest(
        left_path=tmp_path / "l.xlsx",
        right_path=tmp_path / "r.xlsx",
        left_range=SourceRangeSpec.default(),
        right_range=SourceRangeSpec.default(),
        key_columns=["日期"],
    )
    result = controller.action_reconcile(request)
    assert result.ok
    assert result.extra["summary_text"] == AppController.format_reconcile_summary(fake.summary)
    assert result.extra["primary_focus"] == "金額不符"
    assert any("對帳摘要" in m.message for m in result.messages)
    assert any(m.level == "warning" and "重複" in m.message for m in result.messages)


def test_task_flow_runner_reconcile_step(monkeypatch, tmp_path) -> None:
    left = tmp_path / "left.xlsx"
    right = tmp_path / "right.xlsx"
    pd.DataFrame({"日期": ["A"], "金額": [1]}).to_excel(left, index=False)
    pd.DataFrame({"日期": ["B"], "金額": [2]}).to_excel(right, index=False)

    controller = AppController()
    controller.session.files = [
        LoadedFile(path=left, columns=["日期", "金額"]),
        LoadedFile(path=right, columns=["日期", "金額"]),
    ]
    controller.session.output_dir = tmp_path

    from app.services.task_flow_runner import TaskFlowRunner
    from app.services.task_flows import TaskFlow, TaskFlowStep

    runner = TaskFlowRunner(controller)
    flow = TaskFlow(
        task_id="r1",
        name="reconcile_flow",
        resources={},
        steps=(
            TaskFlowStep(
                id="1",
                action="reconcile",
                title="對帳",
                params={
                    "left_file": left.name,
                    "right_file": right.name,
                    "key_columns": "日期",
                    "amount_column": "金額",
                },
            ),
        ),
    )
    outcome = runner.run_one(flow, continue_on_error=False)
    assert outcome.ok
    assert any("僅左邊" in m.message or "對帳摘要" in m.message for m in outcome.messages)
