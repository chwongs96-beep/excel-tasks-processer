"""Tests for task flow scheduler service."""

from __future__ import annotations

from datetime import datetime

from app.core import config
from app.services import task_flow_schedules


def test_create_schedule_and_list(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TASK_FLOW_SCHEDULES_PATH", tmp_path / "task_flow_schedules.json")
    item = task_flow_schedules.create_schedule(
        flow_name="daily_task",
        mode="daily",
        time_hhmm="09:30",
    )
    task_flow_schedules.save_schedule(item)
    items = task_flow_schedules.list_schedules()
    assert len(items) == 1
    assert items[0].flow_name == "daily_task"
    assert items[0].time_hhmm == "09:30"


def test_acquire_due_schedules_no_duplicate_same_minute(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TASK_FLOW_SCHEDULES_PATH", tmp_path / "task_flow_schedules.json")
    item = task_flow_schedules.create_schedule(
        flow_name="daily_task",
        mode="daily",
        time_hhmm="09:30",
    )
    task_flow_schedules.save_schedule(item)
    now = datetime(2026, 5, 21, 9, 30, 10)
    due1 = task_flow_schedules.acquire_due_schedules(now)
    due2 = task_flow_schedules.acquire_due_schedules(now)
    assert len(due1) == 1
    assert len(due2) == 0


def test_weekly_schedule_weekday_match(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TASK_FLOW_SCHEDULES_PATH", tmp_path / "task_flow_schedules.json")
    item = task_flow_schedules.create_schedule(
        flow_name="weekly_task",
        mode="weekly",
        time_hhmm="08:00",
        weekdays=(0, 2),
    )
    task_flow_schedules.save_schedule(item)
    due = task_flow_schedules.acquire_due_schedules(datetime(2026, 5, 20, 8, 0, 0))  # Wed=2
    assert len(due) == 1
    not_due = task_flow_schedules.acquire_due_schedules(datetime(2026, 5, 21, 8, 0, 0))  # Thu=3
    assert len(not_due) == 0
