"""Task flow execution engine (MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import time
from typing import TYPE_CHECKING, Callable

from app.core.schemas import ActionResult, DateSpec, ValidationMessage
from app.services.task_flows import TaskFlow

if TYPE_CHECKING:
    from app.application.app_controller import AppController


@dataclass
class FlowExecutionResult:
    ok: bool
    messages: list[ValidationMessage] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    runs: list["FlowRunRecord"] = field(default_factory=list)
    failed_flow_name: str | None = None
    failed_step_index: int | None = None
    failed_step_title: str | None = None


@dataclass
class StepRunRecord:
    step_index: int
    step_id: str
    title: str
    action: str
    ok: bool
    started_at: str
    ended_at: str
    duration_ms: int
    detail: str | None = None
    message_count: int = 0
    error_count: int = 0
    messages: list[str] = field(default_factory=list)


@dataclass
class FlowRunRecord:
    run_id: str
    flow_name: str
    ok: bool
    started_at: str
    ended_at: str
    duration_ms: int
    outputs: list[str] = field(default_factory=list)
    steps: list[StepRunRecord] = field(default_factory=list)
    failed_step_index: int | None = None
    failed_step_title: str | None = None


class TaskFlowRunner:
    """Run one or many task flows against the current controller session."""

    def __init__(self, controller: "AppController") -> None:
        self._controller = controller

    def run_many(
        self,
        flows: list[TaskFlow],
        *,
        continue_on_error: bool,
        on_flow_start: Callable[[int, str], None] | None = None,
        on_flow_done: Callable[[int, str, bool], None] | None = None,
        start_step_overrides: dict[str, int] | None = None,
    ) -> FlowExecutionResult:
        original_type = self._controller.session.report_type
        original_output = self._controller.session.output_dir
        original_template = self._controller.session.template_path
        all_ok = True
        messages: list[ValidationMessage] = []
        outputs: list[str] = []
        runs: list[FlowRunRecord] = []
        failed_flow_name: str | None = None
        failed_step_index: int | None = None
        failed_step_title: str | None = None
        try:
            for index, flow in enumerate(flows):
                if on_flow_start:
                    on_flow_start(index, flow.name)
                start_step = 1
                if start_step_overrides:
                    start_step = max(1, int(start_step_overrides.get(flow.name, 1)))
                result = self.run_one(
                    flow,
                    continue_on_error=continue_on_error,
                    start_step_index=start_step,
                )
                if on_flow_done:
                    on_flow_done(index, flow.name, result.ok)
                messages.extend(result.messages)
                outputs.extend(result.outputs)
                runs.extend(result.runs)
                if not result.ok:
                    all_ok = False
                    failed_flow_name = result.failed_flow_name or flow.name
                    failed_step_index = result.failed_step_index
                    failed_step_title = result.failed_step_title
                    if not continue_on_error:
                        break
        finally:
            self._controller.sync_session_settings(
                report_type=original_type,
                output_dir=original_output,
                template_path=original_template,
            )
        return FlowExecutionResult(
            ok=all_ok,
            messages=messages,
            outputs=outputs,
            runs=runs,
            failed_flow_name=failed_flow_name,
            failed_step_index=failed_step_index,
            failed_step_title=failed_step_title,
        )

    def run_one(
        self,
        flow: TaskFlow,
        *,
        continue_on_error: bool,
        start_step_index: int = 1,
    ) -> FlowExecutionResult:
        messages: list[ValidationMessage] = []
        outputs: list[str] = []
        resources = flow.resources
        ok = True
        failed_step_index: int | None = None
        failed_step_title: str | None = None
        started_at = _now_iso()
        started_clock = time.perf_counter()
        step_records: list[StepRunRecord] = []
        step_start = max(1, start_step_index)

        self._apply_runtime_settings(resources)
        if _truthy(resources.get("reset_session", "true")):
            self._controller.clear_files()

        for index, step in enumerate(flow.steps, start=1):
            if index < step_start:
                continue
            step_started_at = _now_iso()
            step_clock = time.perf_counter()
            result = self._run_step(
                action=step.action.strip().lower(),
                params=step.params,
                resources=resources,
            )
            prefix = f"[{flow.name}#{index}:{step.title}] "
            for msg in result.messages:
                messages.append(
                    ValidationMessage(
                        level=msg.level,
                        message=prefix + msg.message,
                        source=msg.source,
                        code=msg.code,
                    )
                )
            if result.detail:
                messages.append(ValidationMessage(level="info", message=prefix + result.detail))
            if result.ok and result.report_outcome and result.report_outcome.output_path:
                outputs.append(str(result.report_outcome.output_path))
            step_records.append(
                StepRunRecord(
                    step_index=index,
                    step_id=step.id,
                    title=step.title,
                    action=step.action,
                    ok=result.ok,
                    started_at=step_started_at,
                    ended_at=_now_iso(),
                    duration_ms=int((time.perf_counter() - step_clock) * 1000),
                    detail=result.detail,
                    message_count=len(result.messages),
                    error_count=sum(1 for m in result.messages if m.level == "error"),
                    messages=[f"[{m.level}] {m.message}" for m in result.messages],
                )
            )
            if not result.ok:
                ok = False
                failed_step_index = index
                failed_step_title = step.title
                if not continue_on_error:
                    break
        run = FlowRunRecord(
            run_id=_run_id(),
            flow_name=flow.name,
            ok=ok,
            started_at=started_at,
            ended_at=_now_iso(),
            duration_ms=int((time.perf_counter() - started_clock) * 1000),
            outputs=outputs,
            steps=step_records,
            failed_step_index=failed_step_index,
            failed_step_title=failed_step_title,
        )
        return FlowExecutionResult(
            ok=ok,
            messages=messages,
            outputs=outputs,
            runs=[run],
            failed_flow_name=(flow.name if not ok else None),
            failed_step_index=failed_step_index,
            failed_step_title=failed_step_title,
        )

    def _apply_runtime_settings(self, resources: dict[str, str]) -> None:
        report_type = resources.get("report_type", self._controller.session.report_type)
        if report_type not in {"daily", "weekly", "monthly"}:
            report_type = self._controller.session.report_type
        output_dir = Path(resources.get("output_dir", str(self._controller.session.output_dir)))
        template_path = Path(resources.get("template_path", str(self._controller.session.template_path)))
        self._controller.sync_session_settings(
            report_type=report_type,  # type: ignore[arg-type]
            output_dir=output_dir,
            template_path=template_path,
        )

    def _run_step(self, *, action: str, params: dict[str, str], resources: dict[str, str]) -> ActionResult:
        if action == "import":
            paths = _resolve_import_paths(params, resources)
            if not paths:
                return ActionResult(
                    ok=False,
                    action="task_flow_import",
                    messages=[ValidationMessage(level="error", message="未設定可匯入的檔案或資料夾。")],
                )
            return self._controller.action_import_files(paths)

        if action == "apply_filter_preset":
            preset = params.get("preset") or resources.get("filter_preset", "")
            if not preset:
                return ActionResult(
                    ok=False,
                    action="task_flow_filter",
                    messages=[ValidationMessage(level="error", message="缺少 filter preset 名稱。")],
                )
            return self._controller.apply_filter_preset(preset)

        if action == "apply_range_preset":
            preset = params.get("preset") or resources.get("range_preset", "")
            if not preset:
                return ActionResult(
                    ok=False,
                    action="task_flow_range",
                    messages=[ValidationMessage(level="error", message="缺少 range preset 名稱。")],
                )
            return self._controller.apply_range_preset_to_paths(preset, self._controller.session.file_paths)

        if action == "apply_mapping_preset":
            preset = params.get("preset") or resources.get("mapping_preset", "")
            if not preset:
                return ActionResult(
                    ok=False,
                    action="task_flow_mapping",
                    messages=[ValidationMessage(level="error", message="缺少 mapping preset 名稱。")],
                )
            return self._controller.apply_mapping_preset_to_paths(preset, self._controller.session.file_paths)

        if action == "validate":
            return self._controller.action_validate(_build_date_spec(self._controller.session.report_type, params, resources))

        if action == "preview":
            return self._controller.action_preview(_build_date_spec(self._controller.session.report_type, params, resources))

        if action in {"generate", "generate_report"}:
            return self._controller.action_generate(_build_date_spec(self._controller.session.report_type, params, resources))

        if action == "clear_files":
            self._controller.clear_files()
            return ActionResult(ok=True, action="task_flow_clear", detail="已清空目前檔案清單。")

        return ActionResult(
            ok=False,
            action="task_flow_unknown",
            messages=[ValidationMessage(level="error", message=f"不支援的步驟動作：{action}")],
        )


def _build_date_spec(report_type: str, params: dict[str, str], resources: dict[str, str]) -> DateSpec:
    return DateSpec(
        report_type=report_type,  # type: ignore[arg-type]
        trade_date=_parse_date(params.get("trade_date") or resources.get("trade_date")),
        week_start=_parse_date(params.get("week_start") or resources.get("week_start")),
        week_end=_parse_date(params.get("week_end") or resources.get("week_end")),
        month=_parse_date(params.get("month") or resources.get("month")),
    )


def _resolve_import_paths(params: dict[str, str], resources: dict[str, str]) -> list[Path]:
    from app.services.folder_import import list_excel_files

    files_raw = params.get("files") or resources.get("files", "")
    folder_raw = params.get("folder") or resources.get("source_folder", "")
    recursive = _truthy(params.get("recursive") or resources.get("recursive", "false"))
    paths: list[Path] = []
    if files_raw.strip():
        for token in _split_paths(files_raw):
            path = Path(token)
            if path.is_file():
                paths.append(path)
    elif folder_raw.strip():
        folder = Path(folder_raw)
        if folder.is_dir():
            paths = list_excel_files(folder, recursive=recursive)
    # 去重複保順序
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def _split_paths(raw: str) -> list[str]:
    for sep in (";", "\n", ","):
        raw = raw.replace(sep, "|")
    return [item.strip() for item in raw.split("|") if item.strip()]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
