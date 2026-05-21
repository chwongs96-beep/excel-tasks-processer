"""Application controller — all business orchestration for the UI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.application.import_session import ImportSession
from app.core.logger import get_logger
from app.core.schemas import (
    ActionResult,
    ActionType,
    DateSpec,
    ReportJob,
    ReportType,
    ValidationMessage,
)
from app.services import (
    ExcelReaderService,
    ReportGeneratorService,
    TransformerService,
    ValidatorService,
)
from app.core.file_name_filter import FileNameFilter
from app.core.progress import ProgressReporter
from app.core.range_spec import SourceRangeSpec
from app.services import audit_log
from app.services.consolidation_service import ConsolidateRequest, ConsolidationService
from app.services.excel_clear_service import ExcelClearService
from app.services.pipeline_runner import generate_report_via_pipeline
from app.services.batch_report_service import BatchReportRequest, BatchReportService
from app.services.folder_import import list_excel_files
from app.services.reconcile_service import ReconcileRequest, ReconcileResult, ReconcileService
from app.services.smart_profile_service import ProfileSuggestion, SmartProfileService
from app.core.mapping_utils import remap_preset_for_file

logger = get_logger()


class AppController:
    """Coordinates import, validation, preview, and report generation."""

    def __init__(self) -> None:
        self.session = ImportSession()
        self._reader = ExcelReaderService()
        self._validator = ValidatorService()
        self._transformer = TransformerService()
        self._reporter = ReportGeneratorService()
        self._consolidation = ConsolidationService()
        self._clear = ExcelClearService()
        self._reconcile = ReconcileService()
        self._batch = BatchReportService()
        self._smart_profile = SmartProfileService()

    def sync_session_settings(
        self,
        *,
        report_type: ReportType,
        output_dir: Path,
        template_path: Path,
    ) -> None:
        self.session.report_type = report_type
        self.session.output_dir = Path(output_dir)
        self.session.template_path = Path(template_path)

    def current_date_spec(self, date_spec: DateSpec) -> DateSpec:
        """Ensure date_spec report_type matches session."""
        return DateSpec(
            report_type=self.session.report_type,
            trade_date=date_spec.trade_date,
            week_start=date_spec.week_start,
            week_end=date_spec.week_end,
            month=date_spec.month,
        )

    # ------------------------------------------------------------------
    # Actions (UI calls these only)
    # ------------------------------------------------------------------

    def action_import_folder(self, folder: Path, *, recursive: bool = False) -> ActionResult:
        try:
            paths = list_excel_files(folder, recursive=recursive)
        except ValueError as exc:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[ValidationMessage(level="error", message=str(exc))],
            )
        if not paths:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[
                    ValidationMessage(
                        level="warning",
                        message=f"「{folder}」中沒有找到 .xlsx / .xls 檔案。",
                    )
                ],
            )
        return self.action_import_files(paths)

    def set_watch_folder(
        self,
        folder: Path | None,
        *,
        recursive: bool = False,
        name_filter: FileNameFilter | None = None,
    ) -> None:
        self.session.watch_folder = Path(folder) if folder else None
        self.session.watch_recursive = recursive
        if name_filter is not None:
            self.session.file_name_filter = name_filter
        if folder:
            audit_log.log_operation(
                "watch_folder",
                folder=str(folder),
                filter=name_filter.summary() if name_filter else self.session.file_name_filter.summary(),
            )

    def apply_range_preset_to_paths(
        self,
        preset_name: str,
        paths: list[Path],
    ) -> ActionResult:
        from app.services import range_presets

        try:
            spec = range_presets.load_preset(preset_name)
        except (FileNotFoundError, ValueError) as exc:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[ValidationMessage(level="error", message=str(exc))],
            )

        messages: list[ValidationMessage] = []
        updated = 0
        for path in paths:
            if not any(f.path == path for f in self.session.files):
                continue
            result = self.action_set_file_range(path, spec)
            if result.ok:
                updated += 1
            else:
                messages.extend(result.messages)

        if updated == 0:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=messages
                or [
                    ValidationMessage(
                        level="warning",
                        message="沒有檔案套用範圍 preset。",
                    )
                ],
            )
        return ActionResult(
            ok=True,
            action=ActionType.IMPORT,
            messages=messages,
            detail=f"已將範圍 preset「{preset_name}」套用至 {updated} 個檔案。",
        )

    def apply_mapping_preset_to_paths(
        self,
        preset_name: str,
        paths: list[Path],
    ) -> ActionResult:
        from app.services import mapping_presets

        try:
            preset = mapping_presets.load_preset(preset_name)
        except (FileNotFoundError, ValueError) as exc:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[ValidationMessage(level="error", message=str(exc))],
            )
        merged = dict(self.session.mapping)
        applied = 0
        for loaded in self.session.files:
            if loaded.path not in paths:
                continue
            remapped = remap_preset_for_file(
                preset,
                loaded.path.name,
                loaded.columns,
            )
            if remapped:
                merged.update(remapped)
                applied += 1
        if applied == 0:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[
                    ValidationMessage(
                        level="warning",
                        message="mapping preset 與目前檔案欄位不符，未套用。",
                    )
                ],
            )
        self.set_mapping(merged)
        return ActionResult(
            ok=True,
            action=ActionType.IMPORT,
            detail=f"已將 mapping preset「{preset_name}」套用至 {applied} 個檔案。",
        )

    def apply_filter_preset(self, preset_name: str) -> ActionResult:
        from app.services import filter_presets

        try:
            rules = filter_presets.load_preset(preset_name)
        except (FileNotFoundError, ValueError) as exc:
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[ValidationMessage(level="error", message=str(exc))],
            )
        self.session.file_name_filter = rules
        return ActionResult(
            ok=True,
            action=ActionType.IMPORT,
            detail=f"已套用檔名篩選 preset「{preset_name}」。",
        )

    def action_set_adjustment(self, path: Path, spec: SourceRangeSpec | None = None) -> ActionResult:
        try:
            loaded = self._reader.inspect(path, range_spec=spec or SourceRangeSpec.default())
            self.session.adjustment = loaded
            audit_log.log_operation("set_adjustment", file=path.name)
            return ActionResult(
                ok=True,
                action=ActionType.IMPORT,
                detail=f"已載入調整分錄：{path.name}（{loaded.row_count:,} 列）",
            )
        except Exception as exc:  # noqa: BLE001
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[
                    ValidationMessage(level="error", message=f"無法載入調整分錄：{exc}")
                ],
            )

    def clear_adjustment(self) -> None:
        self.session.adjustment = None

    def action_batch_generate(
        self,
        request: BatchReportRequest,
        progress: ProgressReporter | None = None,
    ) -> ActionResult:
        result = self._batch.run(request, progress=progress)
        messages: list[ValidationMessage] = []
        for text in result.messages:
            messages.append(ValidationMessage(level="info", message=text))
        for day, err in result.failed:
            messages.append(
                ValidationMessage(
                    level="warning",
                    message=f"{day.isoformat()}：{err}",
                    code="batch_failed",
                )
            )
        if result.generated:
            audit_log.log_operation(
                "batch_generate",
                count=len(result.generated),
                dates=[d.isoformat() for d in request.dates],
            )
        return ActionResult(
            ok=result.success,
            action=ActionType.BATCH_GENERATE,
            messages=messages,
            detail=f"已產生 {len(result.generated)} 份報表。" if result.generated else None,
            extra={"paths": [str(p) for p in result.generated]},
        )

    def action_import_files(
        self,
        paths: list[Path],
        progress: ProgressReporter | None = None,
    ) -> ActionResult:
        messages: list[ValidationMessage] = []
        for index, path in enumerate(paths):
            if progress:
                progress.start(index, f"讀取 {path.name}")
            try:
                loaded = self._reader.inspect(path)
                if not any(f.path == loaded.path for f in self.session.files):
                    self.session.files.append(loaded)
                    logger.info("Imported file metadata: %s", loaded.path.name)
                if progress:
                    progress.log(f"  → {loaded.row_count:,} 列")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to inspect %s", path)
                messages.append(
                    ValidationMessage(
                        level="error",
                        message=f"無法讀取「{path.name}」：{exc}",
                        source=str(path),
                        code="read_failed",
                    )
                )
            if progress:
                progress.done(index)

        if progress:
            progress.start(len(paths), "驗證與更新工作階段")
        messages.extend(self._validator.validate_upload_paths(self.session.files))
        self._refresh_raw_preview()
        if progress:
            progress.done(len(paths))

        ok = not any(m.level == "error" for m in messages) and bool(self.session.files)
        detail = f"已匯入 {len(self.session.files)} 個檔案。" if ok else None
        if ok:
            audit_log.log_operation(
                "import",
                file_count=len(paths),
                files=[p.name for p in paths],
            )
        return ActionResult(
            ok=ok,
            action=ActionType.IMPORT,
            messages=messages,
            detail=detail,
        )

    def action_validate(self, date_spec: DateSpec) -> ActionResult:
        spec = self.current_date_spec(date_spec)
        messages = self._collect_validation_messages(spec, include_canonical=True)
        ok = not any(m.level == "error" for m in messages)
        logger.info("Validate %s: ok=%s, messages=%d", spec.report_type, ok, len(messages))
        return ActionResult(
            ok=ok,
            action=ActionType.VALIDATE,
            messages=messages,
            detail="驗證通過。" if ok else None,
        )

    def action_preview(self, date_spec: DateSpec) -> ActionResult:
        spec = self.current_date_spec(date_spec)
        messages = self._collect_validation_messages(spec, include_canonical=True)
        if any(m.level == "error" for m in messages):
            return ActionResult(
                ok=False,
                action=ActionType.PREVIEW,
                messages=messages,
            )

        try:
            frame = self._build_merged_canonical()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Preview transform failed")
            return ActionResult(
                ok=False,
                action=ActionType.PREVIEW,
                messages=[
                    ValidationMessage(
                        level="error",
                        message=f"預覽轉換失敗：{exc}",
                        code="preview_failed",
                    )
                ],
            )

        self.session.transformed_preview = frame
        rows, cols = frame.shape[0], frame.shape[1]
        return ActionResult(
            ok=True,
            action=ActionType.PREVIEW,
            messages=messages,
            detail=f"轉換後預覽：{rows:,} 列 × {cols} 欄",
        )

    def action_generate(self, date_spec: DateSpec) -> ActionResult:
        spec = self.current_date_spec(date_spec)
        messages = self._collect_validation_messages(spec, include_canonical=True)
        if any(m.level == "error" for m in messages):
            return ActionResult(
                ok=False,
                action=ActionType.GENERATE,
                messages=messages,
            )

        job = ReportJob(
            files=self.session.file_paths,
            mapping=self.session.mapping,
            report_type=spec.report_type,
            date_spec=spec,
            output_dir=self.session.output_dir,
            template_path=self.session.template_path,
        )
        outcome = generate_report_via_pipeline(job)

        for note in outcome.messages:
            level = "warning" if outcome.metadata.get("used_fallback") else "info"
            messages.append(ValidationMessage(level=level, message=note))
        for err in outcome.errors:
            messages.append(
                ValidationMessage(level="error", message=err, code="export_failed")
            )

        ok = outcome.success
        logger.info("Generate %s: success=%s path=%s", spec.report_type, ok, outcome.output_path)
        if ok and outcome.output_path:
            audit_log.log_operation(
                "generate_report",
                report_type=spec.report_type,
                output=str(outcome.output_path),
                source_files=[p.name for p in self.session.file_paths],
            )
        return ActionResult(
            ok=ok,
            action=ActionType.GENERATE,
            messages=messages,
            report_outcome=outcome,
            detail=str(outcome.output_path) if outcome.output_path else None,
        )

    # ------------------------------------------------------------------
    # File list mutations (sync, lightweight)
    # ------------------------------------------------------------------

    def remove_file(self, path: Path) -> None:
        self.session.files = [f for f in self.session.files if f.path != path]
        self._refresh_raw_preview()
        if not self.session.files:
            self.session.transformed_preview = pd.DataFrame()

    def clear_files(self) -> None:
        self.session.clear()

    def set_mapping(self, mapping: dict[str, str]) -> None:
        self.session.mapping = dict(mapping)
        logger.info("Mapping updated: %d entries", len(self.session.mapping))

    def suggest_mapping_profile(
        self,
        *,
        filename: str,
        source_columns: list[str],
    ) -> ProfileSuggestion | None:
        return self._smart_profile.suggest(filename=filename, source_columns=source_columns)

    def remember_mapping_profile(
        self,
        *,
        filename: str,
        source_columns: list[str],
        mapping_ui: dict[str, str],
    ) -> None:
        self._smart_profile.record(
            filename=filename,
            source_columns=source_columns,
            mapping=mapping_ui,
        )

    def action_set_file_range(self, path: Path, spec: SourceRangeSpec) -> ActionResult:
        messages: list[ValidationMessage] = []
        try:
            loaded = self._reader.inspect(path, range_spec=spec)
            for index, item in enumerate(self.session.files):
                if item.path == path:
                    self.session.files[index] = loaded
                    break
            self._refresh_raw_preview()
            detail = f"已更新「{path.name}」範圍：{spec.summary()}"
            return ActionResult(ok=True, action=ActionType.IMPORT, messages=messages, detail=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to apply range for %s", path)
            return ActionResult(
                ok=False,
                action=ActionType.IMPORT,
                messages=[
                    ValidationMessage(
                        level="error",
                        message=f"無法套用範圍：{exc}",
                        source=str(path),
                        code="range_invalid",
                    )
                ],
            )

    def action_clear_range(
        self,
        path: Path,
        spec: SourceRangeSpec,
        progress: ProgressReporter | None = None,
    ) -> ActionResult:
        if progress:
            progress.start(0, "開啟活頁簿")
            progress.log(spec.summary())
        if progress:
            progress.done(0)
            progress.start(1, "清除選定範圍")
        result = self._clear.clear_range(path, spec)
        if progress:
            progress.done(1)
            progress.start(2, "儲存檔案")
            if result.success:
                progress.log(result.message)
            progress.done(2)
        if result.success:
            audit_log.log_operation("clear_range", file=path.name, range=spec.summary())
            return ActionResult(
                ok=True,
                action=ActionType.IMPORT,
                detail=result.message,
            )
        return ActionResult(
            ok=False,
            action=ActionType.IMPORT,
            messages=[
                ValidationMessage(level="error", message=result.error or "清除失敗")
            ],
        )

    def action_consolidate(
        self,
        request: ConsolidateRequest,
        progress: ProgressReporter | None = None,
    ) -> ActionResult:
        result = self._consolidation.consolidate(request, progress=progress)
        messages: list[ValidationMessage] = []
        for text in result.messages:
            messages.append(ValidationMessage(level="info", message=text))
        for err in result.errors:
            messages.append(ValidationMessage(level="error", message=err, code="consolidate_failed"))
        if result.success and result.output_path:
            audit_log.log_operation(
                "consolidate",
                sources=[p.name for p, _ in request.sources],
                output=str(result.output_path),
                merge_mode=request.merge_mode,
                use_template=request.use_template,
            )
        return ActionResult(
            ok=result.success,
            action=ActionType.CONSOLIDATE,
            messages=messages,
            detail=str(result.output_path) if result.output_path else None,
            extra={
                "import_after_merge": request.import_after_merge,
                "open_mapping_after_merge": request.open_mapping_after_merge,
            },
        )

    def action_reconcile(self, request: ReconcileRequest) -> ActionResult:
        result = self._reconcile.reconcile(request)
        messages: list[ValidationMessage] = []
        if result.success:
            messages.extend(self._reconcile_result_messages(result))
            audit_log.log_operation(
                "reconcile",
                left=request.left_path.name,
                right=request.right_path.name,
                keys=request.key_columns,
                summary=result.summary,
                output=str(result.output_path) if result.output_path else None,
            )
        for warn in result.warnings:
            messages.append(
                ValidationMessage(level="warning", message=warn, code="reconcile_duplicate_keys")
            )
        for err in result.errors:
            messages.append(ValidationMessage(level="error", message=err, code="reconcile_failed"))
        preview = self._reconcile_preview_frame(result)
        self.session.reconcile_preview = preview
        summary = result.summary
        primary_focus = self._reconcile_primary_focus(summary)
        return ActionResult(
            ok=result.success,
            action=ActionType.RECONCILE,
            messages=messages,
            detail=str(result.output_path) if result.output_path else "對帳完成。",
            extra={
                "summary": summary,
                "preview_rows": len(preview),
                "summary_text": self.format_reconcile_summary(summary),
                "primary_focus": primary_focus,
            },
        )

    @staticmethod
    def format_reconcile_summary(summary: dict[str, int]) -> str:
        """Human-readable reconcile summary (shared by log and dialogs)."""
        only_l = summary.get("僅左邊", 0)
        only_r = summary.get("僅右邊", 0)
        matched = summary.get("鍵相符", 0)
        amt = summary.get("金額不符", 0)
        left_dup = summary.get("左檔重複鍵", 0)
        right_dup = summary.get("右檔重複鍵", 0)
        text = (
            f"僅左邊 {only_l:,} 筆（左有右無）｜僅右邊 {only_r:,} 筆（右有左無）｜"
            f"鍵相符 {matched:,} 筆｜金額不符 {amt:,} 筆"
        )
        if left_dup or right_dup:
            text += (
                f"｜重複鍵：左 {left_dup:,} 個、右 {right_dup:,} 個"
                "（差異筆數可能因重複鍵而膨脹）"
            )
        return text

    @staticmethod
    def _reconcile_primary_focus(summary: dict[str, int]) -> str:
        buckets = {
            "僅左邊": summary.get("僅左邊", 0),
            "僅右邊": summary.get("僅右邊", 0),
            "金額不符": summary.get("金額不符", 0),
        }
        if not any(buckets.values()):
            return "鍵相符"
        label, _ = max(buckets.items(), key=lambda item: item[1])
        return label

    def _reconcile_result_messages(self, result: ReconcileResult) -> list[ValidationMessage]:
        summary = result.summary
        messages = [
            ValidationMessage(
                level="info",
                message="對帳摘要 — " + self.format_reconcile_summary(summary),
            )
        ]
        for key in ("僅左邊", "僅右邊", "金額不符"):
            count = summary.get(key, 0)
            if count:
                messages.append(
                    ValidationMessage(level="info", message=f"{key}：{count:,} 筆", code=f"reconcile_{key}")
                )
        left_dup = summary.get("左檔重複鍵", 0)
        right_dup = summary.get("右檔重複鍵", 0)
        if left_dup or right_dup:
            messages.append(
                ValidationMessage(
                    level="warning",
                    message=(
                        f"重複對帳鍵：左檔 {left_dup:,} 個鍵、右檔 {right_dup:,} 個鍵。"
                        "請補強對帳鍵或先彙總，避免把膨脹列數誤判為資料錯誤。"
                    ),
                    code="reconcile_duplicate_keys",
                )
            )
        return messages

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _collect_validation_messages(
        self,
        spec: DateSpec,
        *,
        include_canonical: bool,
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        messages.extend(self._validator.validate_upload_paths(self.session.files))
        messages.extend(self._validator.validate_mapping(self.session.mapping))
        messages.extend(self._validator.validate_date_spec(spec.report_type, spec))

        if include_canonical and self.session.files:
            try:
                canonical = self._build_merged_canonical()
                messages.extend(
                    self._validator.validate_canonical_frame(
                        canonical,
                        filename=self.session.files[0].path.name,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Canonical build failed during validation")
                messages.append(
                    ValidationMessage(
                        level="error",
                        message=f"無法建立標準化資料以驗證：{exc}",
                        code="canonical_build_failed",
                    )
                )
        return messages

    def _refresh_raw_preview(self) -> None:
        if not self.session.files:
            self.session.raw_preview = pd.DataFrame()
            return
        first = self.session.files[0]
        self.session.raw_preview = self._reader.load_preview(
            first.path,
            range_spec=first.source_range,
        )

    def _build_merged_canonical(self) -> pd.DataFrame:
        if not self.session.files and not self.session.adjustment:
            return pd.DataFrame()
        frames: list[pd.DataFrame] = []
        for loaded in self.session.files:
            raw = self._reader.load_sheet(loaded.path, range_spec=loaded.source_range)
            frame = self._transformer.to_canonical(
                raw,
                self.session.mapping,
                source_name=loaded.path.name,
            )
            frame["_entry_type"] = "source"
            frames.append(frame)
        if self.session.adjustment:
            adj = self.session.adjustment
            raw = self._reader.load_sheet(adj.path, range_spec=adj.source_range)
            frame = self._transformer.to_canonical(
                raw,
                self.session.mapping,
                source_name=adj.path.name,
            )
            frame["_entry_type"] = "adjustment"
            frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _reconcile_preview_frame(result: ReconcileResult, *, limit: int = 200) -> pd.DataFrame:
        parts: list[pd.DataFrame] = []

        def _tag(frame: pd.DataFrame, label: str) -> pd.DataFrame:
            if frame.empty:
                return frame
            work = frame.copy()
            drop = [c for c in work.columns if c in {"_reconcile_key", "_merge"}]
            work = work.drop(columns=drop, errors="ignore")
            work.insert(0, "對帳結果", label)
            return work.head(limit)

        parts.append(_tag(result.only_left, "僅左邊"))
        parts.append(_tag(result.only_right, "僅右邊"))
        parts.append(_tag(result.amount_mismatch, "金額不符"))
        parts = [p for p in parts if not p.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
