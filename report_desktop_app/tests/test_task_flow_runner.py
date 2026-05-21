"""Tests for task flow execution engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.schemas import ActionResult, DateSpec, ReportOutcome
from app.services.task_flows import TaskFlow, TaskFlowStep
from app.services.task_flow_runner import TaskFlowRunner


@dataclass
class _FakeSession:
    report_type: str = "daily"
    output_dir: Path = Path("out")
    template_path: Path = Path("template.xlsx")
    file_paths: list[Path] = field(default_factory=list)


class _FakeController:
    def __init__(self) -> None:
        self.session = _FakeSession()
        self.called: list[str] = []

    def sync_session_settings(self, *, report_type, output_dir, template_path) -> None:
        self.session.report_type = report_type
        self.session.output_dir = output_dir
        self.session.template_path = template_path

    def clear_files(self) -> None:
        self.called.append("clear_files")
        self.session.file_paths = []

    def action_import_files(self, paths: list[Path]) -> ActionResult:
        self.called.append("import")
        self.session.file_paths = list(paths)
        return ActionResult(ok=True, action="import", detail=f"匯入 {len(paths)} 檔")

    def apply_filter_preset(self, preset_name: str) -> ActionResult:
        self.called.append(f"filter:{preset_name}")
        return ActionResult(ok=True, action="filter")

    def apply_range_preset_to_paths(self, preset_name: str, paths: list[Path]) -> ActionResult:
        self.called.append(f"range:{preset_name}:{len(paths)}")
        return ActionResult(ok=True, action="range")

    def apply_mapping_preset_to_paths(self, preset_name: str, paths: list[Path]) -> ActionResult:
        self.called.append(f"mapping:{preset_name}:{len(paths)}")
        return ActionResult(ok=True, action="mapping")

    def action_validate(self, _date_spec: DateSpec) -> ActionResult:
        self.called.append("validate")
        return ActionResult(ok=True, action="validate")

    def action_preview(self, _date_spec: DateSpec) -> ActionResult:
        self.called.append("preview")
        return ActionResult(ok=True, action="preview")

    def action_generate(self, _date_spec: DateSpec) -> ActionResult:
        self.called.append("generate")
        outcome = ReportOutcome(success=True, output_path=Path("out/result.xlsx"))
        return ActionResult(ok=True, action="generate", report_outcome=outcome)


def test_runner_executes_main_steps(tmp_path: Path) -> None:
    src = tmp_path / "a.xlsx"
    src.write_text("x", encoding="utf-8")

    controller = _FakeController()
    runner = TaskFlowRunner(controller)  # type: ignore[arg-type]
    flow = TaskFlow(
        task_id="f1",
        name="flow1",
        resources={"files": str(src), "mapping_preset": "m1", "range_preset": "r1"},
        steps=(
            TaskFlowStep(id="1", action="import", title="匯入", params={}),
            TaskFlowStep(id="2", action="apply_range_preset", title="range", params={}),
            TaskFlowStep(id="3", action="apply_mapping_preset", title="mapping", params={}),
            TaskFlowStep(id="4", action="generate_report", title="產報", params={}),
        ),
    )
    result = runner.run_many([flow], continue_on_error=False)
    assert result.ok is True
    assert "import" in controller.called
    assert "range:r1:1" in controller.called
    assert "mapping:m1:1" in controller.called
    assert "generate" in controller.called
    assert result.outputs == [str(Path("out") / "result.xlsx")]


def test_runner_stops_on_error_when_required() -> None:
    controller = _FakeController()
    runner = TaskFlowRunner(controller)  # type: ignore[arg-type]
    flow = TaskFlow(
        task_id="f2",
        name="bad-flow",
        steps=(
            TaskFlowStep(id="1", action="unknown_action", title="bad", params={}),
            TaskFlowStep(id="2", action="generate_report", title="產報", params={}),
        ),
    )
    result = runner.run_many([flow], continue_on_error=False)
    assert result.ok is False
    assert "generate" not in controller.called
    assert result.failed_flow_name == "bad-flow"
    assert result.failed_step_index == 1
    assert any("不支援的步驟動作" in msg.message for msg in result.messages)


def test_runner_can_resume_from_failed_step(tmp_path: Path) -> None:
    src = tmp_path / "a.xlsx"
    src.write_text("x", encoding="utf-8")
    controller = _FakeController()
    runner = TaskFlowRunner(controller)  # type: ignore[arg-type]
    flow = TaskFlow(
        task_id="f3",
        name="resume-flow",
        resources={"files": str(src), "mapping_preset": "m1"},
        steps=(
            TaskFlowStep(id="1", action="import", title="匯入", params={}),
            TaskFlowStep(id="2", action="apply_mapping_preset", title="mapping", params={}),
            TaskFlowStep(id="3", action="generate_report", title="產報", params={}),
        ),
    )
    result = runner.run_many(
        [flow],
        continue_on_error=False,
        start_step_overrides={"resume-flow": 2},
    )
    assert result.ok is True
    assert "import" not in controller.called
    assert "mapping:m1:0" in controller.called
    assert "generate" in controller.called
