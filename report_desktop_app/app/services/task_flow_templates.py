"""Reusable task-flow templates and setup conversion helpers."""

from __future__ import annotations

from uuid import uuid4

from app.services import filter_presets, mapping_presets, range_presets
from app.services.setup_presets import SetupPreset
from app.services.task_flows import TaskFlow, TaskFlowStep


def suggest_step_params(action: str, *, current_setup: SetupPreset) -> dict[str, str]:
    if action == "apply_filter_preset":
        preset = current_setup.filter_preset or _first_or_empty(filter_presets.list_presets())
        return {"preset": preset} if preset else {}
    if action == "apply_range_preset":
        preset = current_setup.range_preset or _first_or_empty(range_presets.list_presets())
        return {"preset": preset} if preset else {}
    if action == "apply_mapping_preset":
        preset = current_setup.mapping_preset or _first_or_empty(mapping_presets.list_presets())
        return {"preset": preset} if preset else {}
    return {}


def build_blueprint_steps(
    blueprint: tuple[tuple[str, str], ...],
    *,
    current_setup: SetupPreset,
) -> list[TaskFlowStep]:
    steps: list[TaskFlowStep] = []
    for action, title in blueprint:
        steps.append(
            TaskFlowStep(
                id=uuid4().hex[:8],
                action=action,
                title=title,
                params=suggest_step_params(action, current_setup=current_setup),
            )
        )
    return steps


def flow_from_setup(name: str, setup: SetupPreset) -> TaskFlow:
    resources = {
        "report_type": setup.report_type,
        "template_path": setup.template_path,
        "output_dir": setup.output_dir,
        "trade_date": setup.trade_date or "",
        "week_start": setup.week_start or "",
        "week_end": setup.week_end or "",
        "month": setup.month or "",
    }
    steps: list[TaskFlowStep] = [TaskFlowStep(id=uuid4().hex[:8], action="import", title="匯入來源", params={})]
    if setup.filter_preset:
        steps.append(
            TaskFlowStep(
                id=uuid4().hex[:8],
                action="apply_filter_preset",
                title="套用檔名篩選",
                params={"preset": setup.filter_preset},
            )
        )
    if setup.range_preset:
        steps.append(
            TaskFlowStep(
                id=uuid4().hex[:8],
                action="apply_range_preset",
                title="套用範圍",
                params={"preset": setup.range_preset},
            )
        )
    if setup.mapping_preset:
        steps.append(
            TaskFlowStep(
                id=uuid4().hex[:8],
                action="apply_mapping_preset",
                title="套用映射",
                params={"preset": setup.mapping_preset},
            )
        )
    steps.append(
        TaskFlowStep(
            id=uuid4().hex[:8],
            action="generate_report",
            title="產生報表",
            params={},
        )
    )
    return TaskFlow(task_id=uuid4().hex, name=name, resources=resources, steps=tuple(steps))


def _first_or_empty(items: list[str]) -> str:
    return items[0] if items else ""
