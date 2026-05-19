"""Main application window — UI wiring only; logic in AppController."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.application.app_controller import AppController
from app.core.config import APP_NAME, APP_VERSION, OUTPUT_DIR
from app.core.schemas import ActionResult, DateSpec, ReportType, ValidationMessage
from app.ui.dialogs import MappingDialog
from app.ui.help_text import (
    CONSOLIDATE_AND_SHEETS_HELP_HTML,
    RECONCILE_HELP_HTML,
    WORKFLOW_INTRO,
)
from app.ui.session_bar import SessionBar
from app.ui.table_model import DataFrameTableModel
from app.ui.task_runner import BackgroundTaskRunner
from app.ui.widgets import DataPreviewPanel, LogPanel, ReportSettingsPanel, StatusLabel
from app.ui.workflow_bar import WorkflowBar
from app.ui.ui_metrics import (
    LOG_MIN_H,
    SIDEBAR_SPLIT_W,
    WINDOW_DEFAULT_H,
    WINDOW_DEFAULT_W,
    WINDOW_MIN_H,
    WINDOW_MIN_W,
)
from app.ui.styles import apply_theme, current_theme
from app.ui.themes import THEMES, theme_ids
from app.ui.process_steps_dialog import ProcessStepsDialog, ProcessTracker
from app.ui.step_lists import (
    batch_report_steps,
    clear_range_steps,
    consolidate_steps,
    import_file_steps,
)
from app.ui.zoom import UiZoomController


class MainWindow(QMainWindow):
    """Primary window: connects widgets → controller via background tasks."""

    def __init__(self, controller: AppController | None = None) -> None:
        super().__init__()
        self._controller = controller or AppController()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(WINDOW_DEFAULT_W, WINDOW_DEFAULT_H)
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self._workflow_step = 0

        self._raw_model = DataFrameTableModel()
        self._transformed_model = DataFrameTableModel()
        self._reconcile_model = DataFrameTableModel()
        self._status = StatusLabel()
        self._settings = ReportSettingsPanel()
        self._workflow = WorkflowBar()
        self._session_bar = SessionBar()
        self._preview = DataPreviewPanel()
        self._log = LogPanel()
        self._tasks = BackgroundTaskRunner(self)
        self._pending_success: Callable[[ActionResult], None] | None = None
        self._process_dialog: ProcessStepsDialog | None = None

        self._preview.bind_models(
            self._raw_model,
            self._transformed_model,
            self._reconcile_model,
        )
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(60_000)
        self._watch_timer.timeout.connect(self._poll_watch_folder)
        self._settings.output.set_output_path(OUTPUT_DIR)

        self._zoom = UiZoomController(QApplication.instance(), self)
        self._zoom.on_changed(self._on_zoom_changed)

        self._build_layout()
        self._build_menu()
        self._connect_signals()
        self._sync_settings_to_controller()
        self._refresh_session_ui(step=0)
        self._on_zoom_changed(self._zoom.factor())

        self._log.append(WORKFLOW_INTRO, level="info")

    # ------------------------------------------------------------------
    # Layout & signals
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        main_split = QSplitter(Qt.Orientation.Horizontal)

        main_split.addWidget(self._settings)
        main_split.setStretchFactor(0, 0)
        main_split.setCollapsible(0, False)

        center_split = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top.setObjectName("workspace")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        top_layout.addWidget(self._workflow)
        top_layout.addWidget(self._session_bar)
        top_layout.addWidget(self._preview, stretch=1)
        center_split.addWidget(top)
        center_split.addWidget(self._log)
        center_split.setStretchFactor(0, 4)
        center_split.setStretchFactor(1, 1)
        center_split.setSizes([720, LOG_MIN_H + 40])

        main_split.addWidget(center_split)
        main_split.setStretchFactor(1, 1)
        main_split.setSizes([SIDEBAR_SPLIT_W, WINDOW_DEFAULT_W - SIDEBAR_SPLIT_W])

        wrapper = QWidget()
        root = QHBoxLayout(wrapper)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(main_split)
        self.setCentralWidget(wrapper)

        status_bar = QStatusBar()
        status_bar.addWidget(self._status, 1)
        status_bar.addPermanentWidget(self._build_zoom_controls())
        self.setStatusBar(status_bar)

    def _build_zoom_controls(self) -> QWidget:
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 8, 0)
        row.setSpacing(4)

        label = QLabel("介面大小")
        label.setObjectName("zoomUiLabel")

        btn_out = QPushButton("−")
        btn_out.setObjectName("zoomBtn")
        btn_out.setToolTip("縮小（Ctrl + 滾輪向下）")
        btn_out.clicked.connect(self._zoom.zoom_out)

        self._zoom_label = QLabel()
        self._zoom_label.setObjectName("zoomPercent")
        self._zoom_label.setMinimumWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_in = QPushButton("+")
        btn_in.setObjectName("zoomBtn")
        btn_in.setToolTip("放大（Ctrl + 滾輪向上）")
        btn_in.clicked.connect(self._zoom.zoom_in)

        btn_reset = QPushButton("重設")
        btn_reset.setProperty("compact", True)
        btn_reset.style().unpolish(btn_reset)
        btn_reset.style().polish(btn_reset)
        btn_reset.setToolTip("恢復預設大小")
        btn_reset.clicked.connect(self._zoom.reset)

        row.addWidget(label)
        row.addWidget(btn_out)
        row.addWidget(self._zoom_label)
        row.addWidget(btn_in)
        row.addWidget(btn_reset)
        return box

    def _on_zoom_changed(self, factor: float) -> None:
        self._zoom_label.setText(self._zoom.percent_label())

    def _on_theme_selected(self, theme_id: str, checked: bool) -> None:
        if not checked:
            return
        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, theme_id)
        for tid, action in self._theme_actions.items():
            action.setChecked(tid == theme_id)
        name = THEMES[theme_id].display_name
        self._status.show_info(f"配色：{name}")

    def _build_menu(self) -> None:
        view_menu = self.menuBar().addMenu("檢視")

        theme_menu = view_menu.addMenu("配色方案")
        self._theme_actions: dict[str, QAction] = {}
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        active_id = current_theme().id
        for tid in theme_ids():
            theme = THEMES[tid]
            action = QAction(theme.display_name, self)
            action.setCheckable(True)
            action.setChecked(tid == active_id)
            action.triggered.connect(
                lambda checked=False, t=tid: self._on_theme_selected(t, checked)
            )
            theme_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[tid] = action
        view_menu.addSeparator()

        zoom_in = QAction("放大", self)
        zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in.triggered.connect(self._zoom.zoom_in)
        view_menu.addAction(zoom_in)
        zoom_out = QAction("縮小", self)
        zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out.triggered.connect(self._zoom.zoom_out)
        view_menu.addAction(zoom_out)
        zoom_reset = QAction("重設縮放", self)
        zoom_reset.setShortcut("Ctrl+0")
        zoom_reset.triggered.connect(self._zoom.reset)
        view_menu.addAction(zoom_reset)
        view_menu.addSeparator()
        hint = QAction("Ctrl + 滑鼠滾輪可縮放介面", self)
        hint.setEnabled(False)
        view_menu.addAction(hint)

        menu = self.menuBar().addMenu("說明")
        workflow_action = QAction("工作流程說明", self)
        workflow_action.triggered.connect(self._show_workflow_help)
        menu.addAction(workflow_action)
        consolidate_help = QAction("合併與工作表流程", self)
        consolidate_help.triggered.connect(self._show_consolidate_help)
        menu.addAction(consolidate_help)
        reconcile_action = QAction("對帳功能說明", self)
        reconcile_action.triggered.connect(self._show_reconcile_help)
        menu.addAction(reconcile_action)

    def _show_workflow_help(self) -> None:
        QMessageBox.information(self, "工作流程", WORKFLOW_INTRO)

    def _show_html_help(self, title: str, html: str, *, width: int = 640, height: int = 520) -> None:
        from PySide6.QtWidgets import QTextBrowser, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        layout.addWidget(browser)
        dialog.exec()

    def _show_consolidate_help(self) -> None:
        self._show_html_help("合併與工作表流程", CONSOLIDATE_AND_SHEETS_HELP_HTML, width=720, height=560)

    def _show_reconcile_help(self) -> None:
        self._show_html_help("對帳功能說明", RECONCILE_HELP_HTML)

    def _refresh_session_ui(self, *, step: int | None = None) -> None:
        if step is not None:
            self._workflow_step = step
        self._workflow.set_step(self._workflow_step)
        self._session_bar.refresh(self._controller.session)

    def _connect_signals(self) -> None:
        panel = self._settings

        panel.files.add_clicked.connect(self._on_add_files)
        panel.files.add_folder_clicked.connect(self._on_add_folder)
        panel.files.adjustment_clicked.connect(self._on_adjustment)
        panel.files.remove_clicked.connect(self._on_remove_file)
        panel.files.clear_clicked.connect(self._on_clear_files)
        panel.files.mapping_clicked.connect(self._on_mapping)
        panel.files.range_clicked.connect(self._on_range)
        panel.files.consolidate_clicked.connect(self._on_consolidate)
        panel.files.reconcile_clicked.connect(self._on_reconcile)
        panel.files.clear_range_clicked.connect(self._on_clear_range_file)

        panel.report_type_changed.connect(self._on_report_type_changed)
        panel.template_changed.connect(self._on_template_changed)
        panel.output_path_changed.connect(self._on_output_path_changed)
        panel.template.browse_clicked.connect(self._on_browse_template)
        panel.output.browse_clicked.connect(self._on_browse_output)

        panel.actions.validate_clicked.connect(self._on_validate)
        panel.actions.preview_clicked.connect(self._on_preview)
        panel.actions.generate_clicked.connect(self._on_generate)
        panel.actions.open_folder_clicked.connect(self._on_open_output_folder)
        panel.actions.audit_log_clicked.connect(self._on_audit_log)
        panel.actions.batch_generate_clicked.connect(self._on_batch_generate)

        self._tasks.busy_changed.connect(self._set_busy)
        self._tasks.completed.connect(self._on_task_completed)
        self._tasks.failed.connect(self._on_task_failed)

    # ------------------------------------------------------------------
    # Settings sync (no business rules)
    # ------------------------------------------------------------------

    def _sync_settings_to_controller(self) -> None:
        template = self._settings.template.template_path()
        from app.core import config

        template_path = (
            Path(template)
            if template
            else config.TEMPLATE_FILES[self._settings.report_type.report_type()]
        )
        self._controller.sync_session_settings(
            report_type=self._settings.report_type.report_type(),
            output_dir=Path(self._settings.output.output_path()),
            template_path=template_path,
        )

    def _current_date_spec(self) -> DateSpec:
        report_type: ReportType = self._settings.report_type.report_type()
        return self._settings.date_range.build_date_spec(report_type)

    # ------------------------------------------------------------------
    # File import (background)
    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇 Excel 檔案",
            "",
            "Excel (*.xlsx *.xls)",
        )
        if not paths:
            return
        self._sync_settings_to_controller()
        path_objs = [Path(p) for p in paths]
        steps = import_file_steps(path_objs)
        self._run_with_steps(
            "import",
            steps,
            lambda tracker: self._controller.action_import_files(path_objs, tracker),
            self._finish_import,
        )

    def _finish_import(self, result: ActionResult) -> None:
        self._refresh_file_list()
        self._update_raw_preview()
        if result.ok and self._controller.session.files:
            step = 1 if self._controller.session.mapping else 0
            self._refresh_session_ui(step=step)
        self._present_action_result(result, dialog_on_error=True)

    def _on_add_folder(self) -> None:
        from app.ui.dialogs import FolderWatchDialog

        dialog = FolderWatchDialog(
            current=self._controller.session.watch_folder,
            initial_filter=self._controller.session.file_name_filter,
            parent=self,
        )
        if not dialog.exec():
            return
        folder = dialog.folder_path()
        if folder is None:
            QMessageBox.warning(self, "資料夾匯入", "請選擇資料夾路徑。")
            return

        name_filter = dialog.name_filter()
        folder_paths = dialog.matched_paths()
        range_preset = name_filter.range_preset

        self._sync_settings_to_controller()
        if dialog.watch_enabled():
            self._controller.set_watch_folder(
                folder,
                recursive=dialog.recursive(),
                name_filter=name_filter,
            )
            self._watch_timer.start()
            self._log.append(
                f"已啟用資料夾監看：{folder}（{name_filter.summary()}）",
                level="info",
            )
        else:
            self._controller.set_watch_folder(None)
            self._watch_timer.stop()

        if not folder_paths:
            QMessageBox.information(self, "資料夾匯入", "沒有符合關鍵字條件的 Excel。")
            return

        steps = import_file_steps(folder_paths)

        def on_import_done(result: ActionResult) -> None:
            self._finish_import(result)
            if not result.ok or not range_preset:
                return
            preset_result = self._controller.apply_range_preset_to_paths(
                range_preset,
                folder_paths,
            )
            self._present_action_result(
                preset_result,
                dialog_on_error=True,
                dialog_on_success=False,
            )
            if preset_result.ok:
                self._refresh_file_list()
                self._update_raw_preview()

        self._run_with_steps(
            "import_folder",
            steps,
            lambda tracker: self._controller.action_import_files(folder_paths, tracker),
            on_import_done,
        )

    def _poll_watch_folder(self) -> None:
        folder = self._controller.session.watch_folder
        if folder is None or not folder.is_dir():
            return
        from app.services.folder_import import scan_folder

        try:
            scan = scan_folder(
                folder,
                recursive=self._controller.session.watch_recursive,
                name_filter=self._controller.session.file_name_filter,
            )
        except ValueError:
            return
        known = {f.path.resolve() for f in self._controller.session.files}
        new_paths = [p for p in scan.matched if p.resolve() not in known]
        if not new_paths:
            return
        self._log.append(f"監看：發現 {len(new_paths)} 個新檔，正在匯入…", level="info")

        steps = import_file_steps(new_paths)
        self._run_with_steps(
            "watch_import",
            steps,
            lambda tracker: self._controller.action_import_files(new_paths, tracker),
            self._finish_import,
        )

    def _on_adjustment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇調整分錄 Excel",
            "",
            "Excel (*.xlsx *.xls)",
        )
        if not path:
            return
        from app.ui.dialogs import RangeSelectionDialog

        file_path = Path(path)
        try:
            from app.services.excel_reader import ExcelReaderService

            sheets = ExcelReaderService().list_sheet_names(file_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "調整分錄", str(exc))
            return

        current = (
            self._controller.session.adjustment.source_range
            if self._controller.session.adjustment
            else None
        )
        dialog = RangeSelectionDialog(
            path=file_path,
            sheet_names=sheets,
            current=current,
            parent=self,
        )
        if not dialog.exec():
            return
        result = self._controller.action_set_adjustment(file_path, dialog.range_spec())
        self._present_action_result(result, dialog_on_error=True, dialog_on_success=False)
        if result.ok:
            self._log.append("調整分錄將在驗證／產報時併入（_entry_type=adjustment）。", level="info")

    def _on_remove_file(self) -> None:
        index = self._settings.files.selected_index()
        files = self._controller.session.files
        if index < 0 or index >= len(files):
            self._log.append("請先選擇要移除的檔案。", level="warning")
            return
        name = files[index].path.name
        self._controller.remove_file(files[index].path)
        self._refresh_file_list()
        self._update_raw_preview()
        self._transformed_model.set_dataframe(self._controller.session.transformed_preview)
        self._log.append(f"已移除：{name}", level="info")

    def _on_clear_files(self) -> None:
        if not self._controller.session.files:
            return
        if (
            QMessageBox.question(self, "清除檔案", "確定要移除所有已匯入的檔案？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._controller.clear_files()
        self._refresh_file_list()
        self._raw_model.set_dataframe(self._controller.session.raw_preview)
        self._transformed_model.set_dataframe(self._controller.session.transformed_preview)
        self._preview.set_caption("尚未載入資料")
        self._log.append("已清除所有匯入檔案。", level="info")

    def _on_mapping(self, file_index: int | None = None) -> None:
        files = self._controller.session.files
        if not files:
            self._log.append("請先匯入 Excel 再設定欄位映射。", level="warning")
            return
        index = file_index if file_index is not None else self._settings.files.selected_index()
        if index < 0 or index >= len(files):
            index = 0
        loaded = files[index]
        from app.core.mapping_utils import storage_to_ui_mapping, ui_to_storage_mapping

        dialog = MappingDialog(
            source_columns=loaded.columns,
            current_mapping=storage_to_ui_mapping(
                self._controller.session.mapping,
                loaded.path.name,
            ),
            filename=loaded.path.name,
            parent=self,
        )
        if dialog.exec():
            stored = ui_to_storage_mapping(dialog.mapping(), loaded.path.name)
            self._controller.set_mapping(stored)
            self._refresh_session_ui(step=1)
            self._log.append(
                f"「{loaded.path.name}」欄位映射已更新（{len(stored)} 項）。",
                level="info",
            )

    def _on_range(self) -> None:
        files = self._controller.session.files
        index = self._settings.files.selected_index()
        if index < 0 or index >= len(files):
            self._log.append("請先選擇要設定範圍的檔案。", level="warning")
            return
        loaded = files[index]
        from app.ui.dialogs import RangeSelectionDialog

        dialog = RangeSelectionDialog(
            path=loaded.path,
            sheet_names=loaded.sheet_names,
            current=loaded.source_range,
            parent=self,
        )
        if not dialog.exec():
            return
        result = self._controller.action_set_file_range(loaded.path, dialog.range_spec())
        self._refresh_file_list()
        self._update_raw_preview()
        self._present_action_result(result, dialog_on_error=True, dialog_on_success=False)

    def _on_consolidate(self) -> None:
        if not self._controller.session.files:
            self._log.append("請先匯入至少一個 Excel。", level="warning")
            return

        from app.ui.consolidate_wizard import ConsolidateWizard
        from app.ui.merge_advisor_dialog import MergeAdvisorDialog

        files = self._controller.session.files
        advisor = MergeAdvisorDialog(len(files), parent=self)
        if advisor.exec() != QDialog.DialogCode.Accepted:
            return

        if not advisor.use_app_merge():
            advice = advisor.advice()
            tips = "\n".join(f"• {t}" for t in (advice.tips if advice else ()))
            QMessageBox.information(
                self,
                "建議使用 Excel 內建功能",
                f"{advice.reason if advice else ''}\n\n{tips}\n\n"
                "詳見選單：說明 → 合併與工作表流程。",
            )
            return

        mode = advisor.recommended_mode()
        initial_mode = mode if mode in ("single_sheet", "one_sheet_per_file") else None

        wizard = ConsolidateWizard(
            files,
            default_output_dir=self._controller.session.output_dir,
            default_template=self._controller.session.template_path,
            initial_merge_mode=initial_mode,
            parent=self,
        )
        if wizard.exec() != wizard.DialogCode.Accepted:
            return
        request = wizard.build_request()

        steps = consolidate_steps(request.sources)
        self._run_with_steps(
            "consolidate",
            steps,
            lambda tracker: self._controller.action_consolidate(request, tracker),
            lambda r: self._finish_consolidate(r, request),
        )

    def _on_clear_range_file(self) -> None:
        files = self._controller.session.files
        index = self._settings.files.selected_index()
        if index < 0 or index >= len(files):
            self._log.append("請先選擇要清除範圍的檔案。", level="warning")
            return
        loaded = files[index]
        from app.ui.dialogs import RangeSelectionDialog

        dialog = RangeSelectionDialog(
            path=loaded.path,
            sheet_names=loaded.sheet_names,
            current=loaded.source_range,
            parent=self,
        )
        if not dialog.exec():
            return
        spec = dialog.range_spec()
        steps = clear_range_steps()
        self._run_with_steps(
            "clear_range",
            steps,
            lambda tracker: self._controller.action_clear_range(
                loaded.path, spec, tracker
            ),
            lambda r: self._present_action_result(
                r, dialog_on_error=True, dialog_on_success=True, success_title="已清除"
            ),
        )

    def _finish_consolidate(self, result: ActionResult, request) -> None:
        self._present_action_result(
            result,
            dialog_on_error=True,
            dialog_on_success=True,
            success_title="合併完成",
        )
        if not result.ok or not result.detail:
            return
        if not result.extra.get("import_after_merge"):
            return
        merged_path = Path(result.detail)
        import_result = self._controller.action_import_files([merged_path])
        self._refresh_file_list()
        self._update_raw_preview()
        if import_result.ok:
            self._log.append(f"已匯入合併檔：{merged_path.name}", level="success")
        if result.extra.get("open_mapping_after_merge") and self._controller.session.files:
            index = next(
                (
                    i
                    for i, f in enumerate(self._controller.session.files)
                    if f.path == merged_path
                ),
                len(self._controller.session.files) - 1,
            )
            self._settings.files.select_index(index)
            self._on_mapping(file_index=index)

    def _on_reconcile(self) -> None:
        files = self._controller.session.files
        if len(files) < 2:
            self._log.append("資料對帳至少需要兩個已匯入的 Excel。", level="warning")
            return
        from app.ui.dialogs import ReconcileDialog

        dialog = ReconcileDialog(
            files,
            output_dir=self._controller.session.output_dir,
            parent=self,
        )
        if not dialog.exec():
            return
        request = dialog.build_request()
        if request is None:
            QMessageBox.warning(self, "資料對帳", "請至少勾選一個對帳鍵欄位。")
            return

        def work() -> ActionResult:
            return self._controller.action_reconcile(request)

        self._run_background("reconcile", work, self._finish_reconcile)

    def _finish_reconcile(self, result: ActionResult) -> None:
        if result.ok:
            frame = self._controller.session.reconcile_preview
            self._reconcile_model.set_dataframe(frame)
            rows = len(frame)
            summary = result.extra.get("summary") or {}
            only_l = summary.get("僅左邊", 0)
            only_r = summary.get("僅右邊", 0)
            amt = summary.get("金額不符", 0)
            matched = summary.get("鍵相符", 0)
            detail = (
                f"僅左邊 {only_l:,} 筆（左有右無）｜僅右邊 {only_r:,} 筆（右有左無）｜"
                f"鍵相符 {matched:,} 筆｜金額不符 {amt:,} 筆"
            )
            self._preview.set_caption(f"對帳差異預覽：共 {rows:,} 列差異")
            self._preview.set_reconcile_summary(detail)
            self._preview.show_reconcile_tab()
            body = detail
            if result.detail and Path(str(result.detail)).suffix == ".xlsx":
                body += f"\n\n已匯出報告：\n{result.detail}"
            self._present_action_result(
                result,
                dialog_on_error=True,
                dialog_on_success=False,
            )
            QMessageBox.information(self, "對帳結果摘要", body)
        else:
            self._present_action_result(
                result,
                dialog_on_error=True,
                dialog_on_success=False,
            )

    def _on_batch_generate(self) -> None:
        if not self._controller.session.files:
            self._log.append("請先匯入 Excel 再批次產報。", level="warning")
            return
        from app.ui.dialogs import BatchReportDialog

        dialog = BatchReportDialog(parent=self)
        if not dialog.exec():
            return
        self._sync_settings_to_controller()
        request = dialog.build_request(
            files=self._controller.session.file_paths,
            mapping=self._controller.session.mapping,
            output_dir=self._controller.session.output_dir,
            template_path=self._controller.session.template_path,
        )
        if not request.dates:
            QMessageBox.warning(self, "批次產報", "日期區間內沒有符合的日期。")
            return

        steps = batch_report_steps(request.dates)
        self._run_with_steps(
            "batch_generate",
            steps,
            lambda tracker: self._controller.action_batch_generate(request, tracker),
            self._finish_batch_generate,
        )

    def _finish_batch_generate(self, result: ActionResult) -> None:
        self._present_action_result(
            result,
            dialog_on_error=True,
            dialog_on_success=True,
            success_title="批次產報完成",
        )

    def _on_audit_log(self) -> None:
        from app.core import config

        log_path = config.LOGS_DIR / "operations.jsonl"
        if not log_path.is_file():
            QMessageBox.information(
                self,
                "操作紀錄",
                "尚無操作紀錄。匯入、合併、對帳、產報後會自動寫入。",
            )
            return
        text = log_path.read_text(encoding="utf-8")
        lines = text.strip().splitlines()
        tail = "\n".join(lines[-30:]) if lines else "（空）"
        QMessageBox.information(
            self,
            "操作紀錄（最近 30 筆）",
            f"完整紀錄：\n{log_path}\n\n{tail}",
        )

    # ------------------------------------------------------------------
    # Validate (background — may build canonical frame)
    # ------------------------------------------------------------------

    def _on_validate(self) -> None:
        self._sync_settings_to_controller()
        date_spec = self._current_date_spec()

        def work() -> ActionResult:
            return self._controller.action_validate(date_spec)

        self._run_background("validate", work, self._finish_validate)

    def _finish_validate(self, result: ActionResult) -> None:
        if result.ok:
            self._refresh_session_ui(step=2)
        self._present_action_result(result, dialog_on_error=True, dialog_on_success=False)

    # ------------------------------------------------------------------
    # Preview & generate (background)
    # ------------------------------------------------------------------

    def _on_preview(self) -> None:
        self._sync_settings_to_controller()
        date_spec = self._current_date_spec()

        def work() -> ActionResult:
            return self._controller.action_preview(date_spec)

        self._run_background("preview", work, self._finish_preview)

    def _finish_preview(self, result: ActionResult) -> None:
        if result.ok:
            frame = self._controller.session.transformed_preview
            self._transformed_model.set_dataframe(frame)
            self._preview.set_caption(result.detail or "轉換後預覽")
            self._preview.show_transformed_tab()
            self._refresh_session_ui(step=3)
        self._present_action_result(result, dialog_on_error=True, dialog_on_success=False)

    def _on_generate(self) -> None:
        self._sync_settings_to_controller()
        date_spec = self._current_date_spec()

        def work() -> ActionResult:
            return self._controller.action_generate(date_spec)

        self._run_background("generate", work, self._finish_generate)

    def _finish_generate(self, result: ActionResult) -> None:
        if result.ok and result.report_outcome and result.report_outcome.tables:
            first = next(iter(result.report_outcome.tables.values()))
            self._transformed_model.set_dataframe(first)
            self._preview.show_transformed_tab()
            self._refresh_session_ui(step=4)
        self._present_action_result(
            result,
            dialog_on_error=True,
            dialog_on_success=True,
            success_title="報表產生成功",
        )

    # ------------------------------------------------------------------
    # Browse / folder
    # ------------------------------------------------------------------

    def _on_browse_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇報表範本",
            str(self._controller.session.template_path.parent),
            "Excel (*.xlsx)",
        )
        if path:
            self._settings.template.set_template_path(path)

    def _on_browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "選擇輸出資料夾",
            self._settings.output.output_path(),
        )
        if path:
            self._settings.output.set_output_path(path)

    def _on_open_output_folder(self) -> None:
        folder = Path(self._settings.output.output_path())
        folder.mkdir(parents=True, exist_ok=True)
        url = QUrl.fromLocalFile(str(folder.resolve()))
        if not QDesktopServices.openUrl(url) and sys.platform == "win32":
            subprocess.run(["explorer", str(folder)], check=False)

    def _on_report_type_changed(self, report_type: str) -> None:
        self._controller.session.report_type = report_type  # type: ignore[assignment]
        self._log.append(f"報表類型：{report_type}", level="info")

    def _on_template_changed(self, path: str) -> None:
        self._controller.session.template_path = Path(path)
        self._log.append(f"範本：{Path(path).name}", level="info")

    def _on_output_path_changed(self, path: str) -> None:
        self._controller.session.output_dir = Path(path)
        self._log.append(f"輸出目錄：{path}", level="info")

    # ------------------------------------------------------------------
    # Background task plumbing
    # ------------------------------------------------------------------

    def _run_background(
        self,
        task_name: str,
        func: Callable[[], ActionResult],
        on_success: Callable[[ActionResult], None],
    ) -> None:
        self._run_with_steps(task_name, [], func, on_success)

    def _run_with_steps(
        self,
        task_name: str,
        steps: list[str],
        func: Callable[[], ActionResult] | Callable[[ProcessTracker], ActionResult],
        on_success: Callable[[ActionResult], None],
    ) -> None:
        tracker: ProcessTracker | None = None
        if steps:
            dialog = ProcessStepsDialog(steps, self)
            tracker = ProcessTracker()
            dialog.bind_tracker(tracker)
            self._process_dialog = dialog
            dialog.show()
            QApplication.processEvents()

        def work() -> ActionResult:
            if tracker is not None:
                return func(tracker)  # type: ignore[call-arg]
            return func()  # type: ignore[call-arg]

        def wrapped_success(result: ActionResult) -> None:
            if self._process_dialog is not None:
                detail = result.detail or ""
                if not result.ok:
                    errors = [m.message for m in result.messages if m.level == "error"]
                    if errors:
                        detail = errors[0]
                self._process_dialog.finish(result.ok, detail)
            on_success(result)

        self._pending_success = wrapped_success
        if not self._tasks.submit(task_name, work):
            if self._process_dialog is not None:
                self._process_dialog.close()
                self._process_dialog = None
            self._pending_success = None
            QMessageBox.information(
                self,
                "請稍候",
                "正在處理上一項操作，請完成後再試。",
            )

    def _on_task_completed(self, task_name: str, result: object) -> None:
        if isinstance(result, ActionResult) and self._pending_success is not None:
            self._pending_success(result)
            self._pending_success = None
        if not self._tasks.is_busy:
            self._status.show_info("就緒")

    def _on_task_failed(self, task_name: str, message: str) -> None:
        if self._process_dialog is not None:
            self._process_dialog.finish(False, message)
        self._log.append(f"[{task_name}] {message}", level="error")
        self._status.show_error("操作失敗")
        QMessageBox.critical(self, "錯誤", message)

    def _set_busy(self, busy: bool) -> None:
        self._settings.actions.set_actions_enabled(not busy)
        self._settings.files.set_import_enabled(not busy)
        if busy:
            self._status.show_info("處理中，請稍候…")
        else:
            self._status.show_info("就緒")

    # ------------------------------------------------------------------
    # Present results to log / dialogs / status
    # ------------------------------------------------------------------

    def _present_action_result(
        self,
        result: ActionResult,
        *,
        dialog_on_error: bool,
        dialog_on_success: bool = False,
        success_title: str = "完成",
    ) -> None:
        self._log_messages(result.messages)

        errors = [m.message for m in result.messages if m.level == "error"]
        warnings = [m.message for m in result.messages if m.level == "warning"]

        if result.ok:
            self._status.show_success(result.detail or "操作成功")
            if result.detail:
                self._log.append(result.detail, level="success")
            if dialog_on_success:
                body = result.detail or "操作已完成。"
                if result.report_outcome and result.report_outcome.output_path:
                    body = f"{body}\n\n{result.report_outcome.output_path}"
                QMessageBox.information(self, success_title, body)
        else:
            msg = errors[0] if errors else "操作失敗。"
            self._status.show_error(msg)
            if dialog_on_error and errors:
                QMessageBox.warning(self, "無法繼續", "\n".join(errors))
            elif dialog_on_error and warnings:
                QMessageBox.warning(self, "提醒", "\n".join(warnings))

    def _log_messages(self, messages: list[ValidationMessage]) -> None:
        for msg in messages:
            self._log.append(msg.message, level=msg.level)

    def _refresh_file_list(self) -> None:
        items = [
            (f.path.name, f.row_count, f.range_summary())
            for f in self._controller.session.files
        ]
        self._settings.files.set_files(items)
        self._session_bar.refresh(self._controller.session)

    def _update_raw_preview(self) -> None:
        frame = self._controller.session.raw_preview
        self._raw_model.set_dataframe(frame)
        if frame.empty:
            self._preview.set_caption("尚未載入資料")
        else:
            self._preview.set_caption(
                f"原始預覽：{frame.shape[0]:,} 列 × {frame.shape[1]} 欄"
            )
            self._preview.show_raw_tab()
