"""Task flow execution history storage and query helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core import config

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


def _safe_filename(task_name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", task_name.strip())
    return cleaned or "unnamed_task"


def _run_file(task_name: str) -> Path:
    config.TASK_FLOW_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return config.TASK_FLOW_RUNS_DIR / f"{_safe_filename(task_name)}.jsonl"


def append_flow_run(record: dict[str, Any]) -> Path:
    task_name = str(record.get("flow_name", "")).strip() or "unnamed_task"
    path = _run_file(task_name)
    line = json.dumps(record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path


def list_recent_runs(
    *,
    limit: int = 30,
    flow_name: str | None = None,
    keyword: str = "",
    status: str = "all",
) -> list[dict[str, Any]]:
    config.TASK_FLOW_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    files = [_run_file(flow_name)] if flow_name else sorted(config.TASK_FLOW_RUNS_DIR.glob("*.jsonl"))
    rows: list[dict[str, Any]] = []
    kw = keyword.strip().lower()
    wanted_status = status.strip().lower()
    for path in files:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                ok = bool(data.get("ok", False))
                if wanted_status in {"success", "ok"} and not ok:
                    continue
                if wanted_status in {"failed", "error"} and ok:
                    continue
                if kw:
                    blob = json.dumps(data, ensure_ascii=False).lower()
                    if kw not in blob:
                        continue
                rows.append(data)
    rows.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
    return rows[: max(1, limit)]


def summarize_run(run: dict[str, Any]) -> str:
    flow_name = str(run.get("flow_name", ""))
    ok = bool(run.get("ok", False))
    start = str(run.get("started_at", ""))
    end = str(run.get("ended_at", ""))
    duration_ms = int(run.get("duration_ms", 0) or 0)
    status = "成功" if ok else "失敗"
    failed_step = run.get("failed_step_title")
    if isinstance(failed_step, str) and failed_step.strip():
        return (
            f"{flow_name}｜{status}｜{duration_ms}ms｜"
            f"{_fmt_time(start)} -> {_fmt_time(end)}｜失敗步驟：{failed_step}"
        )
    return f"{flow_name}｜{status}｜{duration_ms}ms｜{_fmt_time(start)} -> {_fmt_time(end)}"


def run_details_text(run: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"任務：{run.get('flow_name', '-')}")
    lines.append(f"執行結果：{'成功' if bool(run.get('ok')) else '失敗'}")
    lines.append(f"開始：{_fmt_time(str(run.get('started_at', '')))}")
    lines.append(f"結束：{_fmt_time(str(run.get('ended_at', '')))}")
    lines.append(f"耗時：{int(run.get('duration_ms', 0) or 0)} ms")
    outputs = run.get("outputs", [])
    if isinstance(outputs, list) and outputs:
        lines.append("輸出：")
        lines.extend([f"  - {item}" for item in outputs])
    lines.append("")
    lines.append("步驟明細：")
    steps = run.get("steps", [])
    if not isinstance(steps, list) or not steps:
        lines.append("  （無步驟紀錄）")
        return "\n".join(lines)
    for step in steps:
        if not isinstance(step, dict):
            continue
        idx = step.get("step_index", "-")
        title = step.get("title", "")
        action = step.get("action", "")
        ok = bool(step.get("ok", False))
        lines.append(f"{idx}. {title} ({action}) - {'OK' if ok else 'FAILED'}")
        lines.append(f"    耗時：{int(step.get('duration_ms', 0) or 0)} ms")
        detail = str(step.get("detail") or "").strip()
        if detail:
            lines.append(f"    詳細：{detail}")
        messages = step.get("messages", [])
        if isinstance(messages, list) and messages:
            for msg in messages:
                lines.append(f"    訊息：{msg}")
    return "\n".join(lines)


def _fmt_time(value: str) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M:%S")
    except ValueError:
        return value
