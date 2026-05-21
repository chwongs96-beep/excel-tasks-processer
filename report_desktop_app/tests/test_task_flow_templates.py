"""Tests for task flow template helpers."""

from __future__ import annotations

from app.services.setup_presets import SetupPreset
from app.services import task_flow_templates


def _setup(**kwargs) -> SetupPreset:
    return SetupPreset(
        name=kwargs.get("name", "s1"),
        report_type=kwargs.get("report_type", "daily"),
        template_path=kwargs.get("template_path", "tmpl.xlsx"),
        output_dir=kwargs.get("output_dir", "out"),
        trade_date=kwargs.get("trade_date"),
        week_start=kwargs.get("week_start"),
        week_end=kwargs.get("week_end"),
        month=kwargs.get("month"),
        mapping_preset=kwargs.get("mapping_preset"),
        range_preset=kwargs.get("range_preset"),
        filter_preset=kwargs.get("filter_preset"),
    )


def test_suggest_step_params_prefer_setup_values() -> None:
    setup = _setup(mapping_preset="mX", range_preset="rX", filter_preset="fX")
    assert task_flow_templates.suggest_step_params("apply_mapping_preset", current_setup=setup) == {"preset": "mX"}
    assert task_flow_templates.suggest_step_params("apply_range_preset", current_setup=setup) == {"preset": "rX"}
    assert task_flow_templates.suggest_step_params("apply_filter_preset", current_setup=setup) == {"preset": "fX"}


def test_suggest_step_params_fallback_to_existing_presets(monkeypatch) -> None:
    setup = _setup()
    monkeypatch.setattr(task_flow_templates.mapping_presets, "list_presets", lambda: ["m1"])
    monkeypatch.setattr(task_flow_templates.range_presets, "list_presets", lambda: ["r1"])
    monkeypatch.setattr(task_flow_templates.filter_presets, "list_presets", lambda: ["f1"])
    assert task_flow_templates.suggest_step_params("apply_mapping_preset", current_setup=setup) == {"preset": "m1"}
    assert task_flow_templates.suggest_step_params("apply_range_preset", current_setup=setup) == {"preset": "r1"}
    assert task_flow_templates.suggest_step_params("apply_filter_preset", current_setup=setup) == {"preset": "f1"}


def test_build_blueprint_steps_includes_default_params(monkeypatch) -> None:
    setup = _setup()
    monkeypatch.setattr(task_flow_templates.mapping_presets, "list_presets", lambda: ["m1"])
    blueprint = (("apply_mapping_preset", "套用映射"), ("generate_report", "產生報表"))
    steps = task_flow_templates.build_blueprint_steps(blueprint, current_setup=setup)
    assert len(steps) == 2
    assert steps[0].action == "apply_mapping_preset"
    assert steps[0].params == {"preset": "m1"}
    assert steps[1].action == "generate_report"
    assert steps[1].params == {}


def test_flow_from_setup_keeps_setup_binding() -> None:
    setup = _setup(name="daily_A", mapping_preset="mA", range_preset="rA", filter_preset="fA")
    flow = task_flow_templates.flow_from_setup("daily_A_task", setup)
    assert flow.name == "daily_A_task"
    assert flow.resources["report_type"] == "daily"
    actions = [item.action for item in flow.steps]
    assert actions == [
        "import",
        "apply_filter_preset",
        "apply_range_preset",
        "apply_mapping_preset",
        "generate_report",
    ]
