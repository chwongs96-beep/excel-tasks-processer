"""Task flow scheduler persistence and due-check logic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.core import config


@dataclass(frozen=True)
class TaskSchedule:
    schedule_id: str
    flow_name: str
    mode: str  # daily | weekly
    time_hhmm: str
    weekdays: tuple[int, ...] = ()
    enabled: bool = True
    continue_on_error: bool = False
    last_trigger_key: str = ""

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "flow_name": self.flow_name,
            "mode": self.mode,
            "time_hhmm": self.time_hhmm,
            "weekdays": list(self.weekdays),
            "enabled": self.enabled,
            "continue_on_error": self.continue_on_error,
            "last_trigger_key": self.last_trigger_key,
        }

    @staticmethod
    def from_dict(data: dict) -> "TaskSchedule":
        weekdays_raw = data.get("weekdays", [])
        weekdays: tuple[int, ...] = ()
        if isinstance(weekdays_raw, list):
            weekdays = tuple(
                int(item)
                for item in weekdays_raw
                if isinstance(item, int) and 0 <= item <= 6
            )
        mode = str(data.get("mode", "daily")).strip().lower()
        if mode not in {"daily", "weekly"}:
            mode = "daily"
        return TaskSchedule(
            schedule_id=str(data.get("schedule_id", uuid4().hex)),
            flow_name=str(data.get("flow_name", "")).strip(),
            mode=mode,
            time_hhmm=_normalize_hhmm(str(data.get("time_hhmm", "09:00"))),
            weekdays=weekdays,
            enabled=bool(data.get("enabled", True)),
            continue_on_error=bool(data.get("continue_on_error", False)),
            last_trigger_key=str(data.get("last_trigger_key", "")),
        )


def list_schedules() -> list[TaskSchedule]:
    return _load_doc()


def save_schedule(schedule: TaskSchedule) -> None:
    items = _load_doc()
    replaced = False
    for idx, item in enumerate(items):
        if item.schedule_id == schedule.schedule_id:
            items[idx] = schedule
            replaced = True
            break
    if not replaced:
        items.append(schedule)
    _save_doc(items)


def delete_schedule(schedule_id: str) -> None:
    items = [item for item in _load_doc() if item.schedule_id != schedule_id]
    _save_doc(items)


def create_schedule(
    *,
    flow_name: str,
    mode: str,
    time_hhmm: str,
    weekdays: tuple[int, ...] = (),
    enabled: bool = True,
    continue_on_error: bool = False,
) -> TaskSchedule:
    mode_text = mode.strip().lower()
    if mode_text not in {"daily", "weekly"}:
        raise ValueError("mode 必須是 daily 或 weekly。")
    schedule = TaskSchedule(
        schedule_id=uuid4().hex,
        flow_name=flow_name.strip(),
        mode=mode_text,
        time_hhmm=_normalize_hhmm(time_hhmm),
        weekdays=tuple(sorted(set(weekdays))),
        enabled=enabled,
        continue_on_error=continue_on_error,
    )
    if not schedule.flow_name:
        raise ValueError("flow_name 不可為空。")
    if schedule.mode == "weekly" and not schedule.weekdays:
        raise ValueError("weekly 排程需要至少一個 weekday。")
    return schedule


def acquire_due_schedules(now: datetime | None = None) -> list[TaskSchedule]:
    current = now or datetime.now()
    key = current.strftime("%Y%m%d%H%M")
    hhmm = current.strftime("%H:%M")
    weekday = current.weekday()
    items = _load_doc()
    due: list[TaskSchedule] = []
    updated: list[TaskSchedule] = []
    changed = False
    for item in items:
        if not item.enabled:
            updated.append(item)
            continue
        if item.time_hhmm != hhmm:
            updated.append(item)
            continue
        if item.mode == "weekly" and weekday not in set(item.weekdays):
            updated.append(item)
            continue
        if item.last_trigger_key == key:
            updated.append(item)
            continue
        triggered = TaskSchedule(
            schedule_id=item.schedule_id,
            flow_name=item.flow_name,
            mode=item.mode,
            time_hhmm=item.time_hhmm,
            weekdays=item.weekdays,
            enabled=item.enabled,
            continue_on_error=item.continue_on_error,
            last_trigger_key=key,
        )
        due.append(triggered)
        updated.append(triggered)
        changed = True
    if changed:
        _save_doc(updated)
    return due


def _normalize_hhmm(value: str) -> str:
    text = value.strip()
    try:
        parsed = datetime.strptime(text, "%H:%M")
    except ValueError as exc:
        raise ValueError("time_hhmm 需為 HH:MM（24 小時）格式。") from exc
    return parsed.strftime("%H:%M")


def _load_doc() -> list[TaskSchedule]:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.TASK_FLOW_SCHEDULES_PATH
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = payload.get("schedules", []) if isinstance(payload, dict) else []
    result: list[TaskSchedule] = []
    if isinstance(items, list):
        for raw in items:
            if isinstance(raw, dict):
                result.append(TaskSchedule.from_dict(raw))
    return result


def _save_doc(items: list[TaskSchedule]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "schedules": [item.to_dict() for item in items]}
    config.TASK_FLOW_SCHEDULES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
