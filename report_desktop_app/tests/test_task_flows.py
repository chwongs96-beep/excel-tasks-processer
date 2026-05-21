"""Tests for task flow persistence schema."""

from __future__ import annotations

from pathlib import Path

from app.core import config
from app.services import task_flows
from app.services.task_flows import TaskFlow, TaskFlowStep


def test_task_flow_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "TASK_FLOWS_DIR", tmp_path)
    flow = TaskFlow(
        task_id="task001",
        name="daily_batch",
        description="daily auto flow",
        version=2,
        enabled=True,
        tags=("daily", "auto"),
        resources={"source_folder": "C:/data", "output_dir": "C:/out"},
        steps=(
            TaskFlowStep(id="s1", action="import", title="匯入", params={"recursive": "true"}),
            TaskFlowStep(id="s2", action="generate_report", title="產生報表", params={}),
        ),
    )
    task_flows.save_flow(flow)
    loaded = task_flows.load_flow("daily_batch")
    assert loaded.task_id == "task001"
    assert loaded.name == "daily_batch"
    assert loaded.version == 2
    assert loaded.tags == ("daily", "auto")
    assert len(loaded.steps) == 2
    assert loaded.steps[0].params["recursive"] == "true"


def test_task_flow_list_and_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "TASK_FLOWS_DIR", tmp_path)
    flow = TaskFlow(task_id="x", name="to_delete")
    task_flows.save_flow(flow)
    assert "to_delete" in task_flows.list_flows()
    task_flows.delete_flow("to_delete")
    assert "to_delete" not in task_flows.list_flows()


def test_task_flow_export_import(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "TASK_FLOWS_DIR", tmp_path / "flows")
    flow1 = TaskFlow(task_id="a1", name="flow_a")
    flow2 = TaskFlow(task_id="b1", name="flow_b")
    task_flows.save_flow(flow1)
    task_flows.save_flow(flow2)
    export_path = tmp_path / "export.json"
    task_flows.export_flows(["flow_a", "flow_b"], export_path)
    task_flows.delete_flow("flow_a")
    task_flows.delete_flow("flow_b")
    imported, skipped = task_flows.import_flows(export_path, overwrite=False)
    assert imported == 2
    assert skipped == 0
    assert set(task_flows.list_flows()) == {"flow_a", "flow_b"}
