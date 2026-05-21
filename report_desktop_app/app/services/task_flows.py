"""Task flow schema and persistence helpers (MVP)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.core import config

_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class TaskFlowStep:
    id: str
    action: str
    title: str
    params: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "title": self.title,
            "params": dict(self.params),
        }

    @staticmethod
    def from_dict(data: dict) -> "TaskFlowStep":
        params = data.get("params", {})
        if not isinstance(params, dict):
            params = {}
        return TaskFlowStep(
            id=str(data.get("id", uuid4().hex[:8])),
            action=str(data.get("action", "custom")),
            title=str(data.get("title", "未命名步驟")),
            params={str(k): str(v) for k, v in params.items()},
        )


@dataclass(frozen=True)
class TaskFlow:
    task_id: str
    name: str
    description: str = ""
    version: int = 1
    enabled: bool = True
    tags: tuple[str, ...] = ()
    resources: dict[str, str] = field(default_factory=dict)
    steps: tuple[TaskFlowStep, ...] = ()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "tags": list(self.tags),
            "resources": dict(self.resources),
            "steps": [step.to_dict() for step in self.steps],
        }

    @staticmethod
    def from_dict(data: dict) -> "TaskFlow":
        resources = data.get("resources", {})
        if not isinstance(resources, dict):
            resources = {}
        tags_raw = data.get("tags", [])
        tags = tuple(str(item) for item in tags_raw) if isinstance(tags_raw, list) else ()
        steps_raw = data.get("steps", [])
        steps: list[TaskFlowStep] = []
        if isinstance(steps_raw, list):
            for item in steps_raw:
                if isinstance(item, dict):
                    steps.append(TaskFlowStep.from_dict(item))
        return TaskFlow(
            task_id=str(data.get("task_id", uuid4().hex)),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")),
            version=int(data.get("version", 1)),
            enabled=bool(data.get("enabled", True)),
            tags=tags,
            resources={str(k): str(v) for k, v in resources.items()},
            steps=tuple(steps),
        )


def _flow_path(name: str) -> Path:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("任務名稱不可為空。")
    if _INVALID_NAME.search(cleaned):
        raise ValueError("任務名稱含有不允許的字元。")
    config.TASK_FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    return config.TASK_FLOWS_DIR / f"{cleaned}.json"


def list_flows() -> list[str]:
    config.TASK_FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.stem for path in config.TASK_FLOWS_DIR.glob("*.json"))


def load_flow(name: str) -> TaskFlow:
    path = _flow_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"找不到任務流程：{name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"任務流程格式錯誤：{name}")
    flow = TaskFlow.from_dict(data)
    if not flow.name:
        flow = TaskFlow(
            task_id=flow.task_id,
            name=name,
            description=flow.description,
            version=flow.version,
            enabled=flow.enabled,
            tags=flow.tags,
            resources=flow.resources,
            steps=flow.steps,
        )
    return flow


def save_flow(flow: TaskFlow) -> Path:
    path = _flow_path(flow.name)
    payload = flow.to_dict()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def delete_flow(name: str) -> None:
    path = _flow_path(name)
    if path.exists():
        path.unlink()


def export_flows(names: list[str], export_path: Path) -> Path:
    if not names:
        raise ValueError("沒有可匯出的任務。")
    flows: list[dict] = []
    for name in names:
        flow = load_flow(name)
        flows.append(flow.to_dict())
    payload = {
        "version": 1,
        "flows": flows,
    }
    export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return export_path


def import_flows(import_path: Path, *, overwrite: bool = False) -> tuple[int, int]:
    if not import_path.is_file():
        raise FileNotFoundError(f"找不到匯入檔案：{import_path}")
    data = json.loads(import_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("匯入檔案格式錯誤。")
    items = data.get("flows", [])
    if not isinstance(items, list):
        raise ValueError("匯入檔案缺少 flows 陣列。")
    imported = 0
    skipped = 0
    existing = set(list_flows())
    for raw in items:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        flow = TaskFlow.from_dict(raw)
        name = flow.name.strip()
        if not name:
            skipped += 1
            continue
        if name in existing and not overwrite:
            skipped += 1
            continue
        save_flow(flow)
        existing.add(name)
        imported += 1
    return imported, skipped
