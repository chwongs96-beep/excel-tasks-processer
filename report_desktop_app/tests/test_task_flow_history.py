"""Tests for task flow execution history storage."""

from __future__ import annotations

from app.core import config
from app.services import task_flow_history


def test_append_and_list_recent_runs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "TASK_FLOW_RUNS_DIR", tmp_path)
    task_flow_history.append_flow_run(
        {
            "run_id": "r1",
            "flow_name": "daily_flow",
            "ok": True,
            "started_at": "2026-05-21T01:00:00+00:00",
            "ended_at": "2026-05-21T01:00:02+00:00",
            "duration_ms": 2000,
        }
    )
    task_flow_history.append_flow_run(
        {
            "run_id": "r2",
            "flow_name": "daily_flow",
            "ok": False,
            "started_at": "2026-05-21T02:00:00+00:00",
            "ended_at": "2026-05-21T02:00:01+00:00",
            "duration_ms": 1000,
            "failed_step_title": "套用映射",
        }
    )
    runs = task_flow_history.list_recent_runs(limit=5, flow_name="daily_flow")
    assert len(runs) == 2
    assert runs[0]["run_id"] == "r2"
    text = task_flow_history.summarize_run(runs[0])
    assert "失敗步驟" in text


def test_run_details_text_contains_step_messages() -> None:
    text = task_flow_history.run_details_text(
        {
            "flow_name": "demo",
            "ok": False,
            "started_at": "2026-05-21T02:00:00+00:00",
            "ended_at": "2026-05-21T02:00:05+00:00",
            "duration_ms": 5000,
            "steps": [
                {
                    "step_index": 1,
                    "title": "匯入",
                    "action": "import",
                    "ok": False,
                    "duration_ms": 123,
                    "messages": ["[error] 無法讀取檔案"],
                }
            ],
        }
    )
    assert "步驟明細" in text
    assert "無法讀取檔案" in text
