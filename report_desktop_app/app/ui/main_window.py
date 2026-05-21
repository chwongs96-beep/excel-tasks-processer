"""Main application window — UI wiring only; logic in AppController."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QResizeEvent,
    QShortcut,
)
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
from app.core.config import ALLOWED_EXTENSIONS, APP_NAME, APP_VERSION, OUTPUT_DIR
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
from app.ui.ui_utils import (
    card_frame,
    mark_primary,
    mark_secondary,
    sized_button,
    themed_help_css,
    wrap_help_html,
)
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
from app.services.setup_presets import SetupPreset
from app.services import setup_presets, task_flow_history, task_flow_schedules, task_flows
from app.services.task_flow_runner import TaskFlowRunner


class MainWindow(QMainWindow):
    """Primary window: connects widgets → controller via background tasks."""
    _PREF_REPORT_TYPE = "ui/prefs/report_type"
    _PREF_TEMPLATE = "ui/prefs/template_path"
    _PREF_OUTPUT = "ui/prefs/output_path"
    _PREF_LAST_OPEN_DIR = "ui/prefs/last_open_dir"
    _PREF_HIGH_READABILITY = "ui/prefs/high_readability"
    _PREF_ONBOARD_SEEN = "ui/prefs/onboard_seen"

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
        self.setAcceptDrops(True)
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(60_000)
        self._watch_timer.timeout.connect(self._poll_watch_folder)
        self._settings.output.set_output_path(OUTPUT_DIR)

        self._zoom = UiZoomController(QApplication.instance(), self)
        self._zoom.on_changed(self._on_zoom_changed)

        self._build_layout()
        self._build_menu()
        self._load_user_preferences()
        self._connect_signals()
        self._bind_global_shortcuts()
        self._sync_settings_to_controller()
        self._refresh_session_ui(step=0)
        self._on_zoom_changed(self._zoom.factor())

        self._log.append(WORKFLOW_INTRO, level="info")
        self._show_onboarding_once()

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
        top_layout.addWidget(self._build_quickstart_card())
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

    def _build_quickstart_card(self) -> QWidget:
        frame, layout = card_frame("新手導引")
        intro = QLabel("三步完成常見操作：")
        intro.setProperty("role", "caption")
        layout.addWidget(intro)

        row = QHBoxLayout()
        row.setSpacing(8)
        quick_report = self._quickstart_button(
            "⚡",
            "快速產報",
            "已匯入後直接產報",
        )
        quick_import_reconcile = self._quickstart_button(
            "🔍",
            "匯入並對帳",
            "缺檔時會先引導匯入",
        )
        quick_task = self._quickstart_button(
            "🤖",
            "任務一鍵跑",
            "開啟任務管理並執行",
        )
        mark_primary(quick_report)
        mark_secondary(quick_import_reconcile)
        mark_secondary(quick_task)
        self._quick_btn_report = quick_report
        self._quick_btn_reconcile = quick_import_reconcile
        self._quick_btn_task = quick_task
        quick_report.setToolTip("已匯入資料後，直接產生報表。")
        quick_import_reconcile.setToolTip("引導你先匯入，再進入對帳。")
        quick_task.setToolTip("開啟任務管理，一鍵執行流程。")
        quick_report.clicked.connect(self._on_generate)
        quick_import_reconcile.clicked.connect(self._on_quick_import_reconcile)
        quick_task.clicked.connect(self._on_task_flow_manager)
        row.addWidget(quick_report)
        row.addWidget(quick_import_reconcile)
        row.addWidget(quick_task)
        row.addStretch()
        layout.addLayout(row)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        step1 = QLabel("① 先選入口")
        step2 = QLabel("② 跟著提示")
        step3 = QLabel("③ 檢視輸出")
        for chip in (step1, step2, step3):
            chip.setProperty("role", "stat-chip")
            chips.addWidget(chip)
        chips.addStretch()
        layout.addLayout(chips)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._quick_status_report = QLabel()
        self._quick_status_reconcile = QLabel()
        self._quick_status_task = QLabel()
        for label in (
            self._quick_status_report,
            self._quick_status_reconcile,
            self._quick_status_task,
        ):
            label.setWordWrap(True)
            label.setProperty("role", "quickstart-status-muted")
            status_row.addWidget(label, stretch=1)
        layout.addLayout(status_row)
        self._refresh_quickstart_status()
        return frame

    def _quickstart_button(self, icon: str, title: str, subtitle: str) -> QPushButton:
        btn = sized_button(f"{icon}  {title}\n{subtitle}", min_width=170)
        btn.setProperty("quickstart", True)
        btn.setMinimumHeight(72)
        return btn

    def _on_quick_import_reconcile(self) -> None:
        if len(self._controller.session.files) < 2:
            self._on_add_files()
            QMessageBox.information(
                self,
                "匯入並對帳",
                "已進入匯入流程；請至少匯入兩個檔案後再點一次此按鈕進行對帳。",
            )
            return
        self._on_reconcile()

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
        self._zoom_btn_out = btn_out

        self._zoom_label = QLabel()
        self._zoom_label.setObjectName("zoomPercent")
        self._zoom_label.setMinimumWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_in = QPushButton("+")
        btn_in.setObjectName("zoomBtn")
        btn_in.setToolTip("放大（Ctrl + 滾輪向上）")
        btn_in.clicked.connect(self._zoom.zoom_in)
        self._zoom_btn_in = btn_in

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
        self._zoom_btn_in.setEnabled(self._zoom.can_zoom_in())
        self._zoom_btn_out.setEnabled(self._zoom.can_zoom_out())
        if hasattr(self, "_zoom_preset_actions"):
            current = int(round(factor * 100))
            for percent, action in self._zoom_preset_actions.items():
                action.setChecked(abs(percent - current) <= 1)
        self._status.show_info(f"介面縮放：{self._zoom.percent_label()}")

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
        high_readability = QAction("高可讀模式", self)
        high_readability.setCheckable(True)
        high_readability.setChecked(bool(QSettings().value(self._PREF_HIGH_READABILITY, False, type=bool)))
        high_readability.triggered.connect(self._on_toggle_high_readability)
        view_menu.addAction(high_readability)
        self._high_readability_action = high_readability
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
        zoom_presets = view_menu.addMenu("固定縮放")
        preset_group = QActionGroup(self)
        preset_group.setExclusive(True)
        self._zoom_preset_actions: dict[int, QAction] = {}
        for percent in (75, 90, 100, 110, 125, 150):
            action = QAction(f"{percent}%", self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, p=percent: self._zoom.set_percent(p)
            )
            preset_group.addAction(action)
            zoom_presets.addAction(action)
            self._zoom_preset_actions[percent] = action
        view_menu.addSeparator()
        hint = QAction("Ctrl + 滑鼠滾輪可縮放介面", self)
        hint.setEnabled(False)
        view_menu.addAction(hint)
        view_menu.addSeparator()
        setup_runner = QAction("Setup 批次執行…", self)
        setup_runner.triggered.connect(self._on_setup_runner)
        view_menu.addAction(setup_runner)
        task_manager = QAction("任務流程管理…", self)
        task_manager.triggered.connect(self._on_task_flow_manager)
        view_menu.addAction(task_manager)

        menu = self.menuBar().addMenu("說明")
        guide_action = QAction("完整使用手冊（繁體中文）", self)
        guide_action.triggered.connect(self._show_user_guide)
        menu.addAction(guide_action)
        menu.addSeparator()
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

    def _show_user_guide(self) -> None:
        from app.core import config

        guide_path = config.REPO_ROOT / "docs" / "USER_GUIDE_zh-TW.md"
        if not guide_path.is_file():
            QMessageBox.warning(
                self,
                "使用手冊",
                f"找不到手冊檔案：\n{guide_path}",
            )
            return

        from PySide6.QtWidgets import QPushButton, QTextBrowser, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("完整使用手冊（繁體中文）")
        dialog.resize(780, 640)
        layout = QVBoxLayout(dialog)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.document().setDefaultStyleSheet(themed_help_css())
        try:
            browser.setMarkdown(guide_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            browser.setPlainText(guide_path.read_text(encoding="utf-8"))
            browser.append(f"\n\n（Markdown 顯示失敗：{exc}）")

        open_btn = QPushButton("以系統預設程式開啟檔案…")
        open_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(guide_path.resolve())))
        )

        layout.addWidget(browser, stretch=1)
        layout.addWidget(open_btn)
        dialog.exec()

    def _show_html_help(self, title: str, html: str, *, width: int = 640, height: int = 520) -> None:
        from PySide6.QtWidgets import QTextBrowser, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(wrap_help_html(html))
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
        self._refresh_quickstart_status()

    def _refresh_quickstart_status(self) -> None:
        if not hasattr(self, "_quick_status_report"):
            return

        file_count = len(self._controller.session.files)
        has_mapping = bool(self._controller.session.mapping)
        task_count = len(task_flows.list_flows())

        if file_count <= 0:
            self._set_quick_status(
                self._quick_status_report,
                "● 尚未匯入檔案",
                "quickstart-status-muted",
            )
        elif has_mapping:
            self._set_quick_status(
                self._quick_status_report,
                f"● 產報就緒（{file_count} 檔）",
                "quickstart-status-ok",
            )
        else:
            self._set_quick_status(
                self._quick_status_report,
                f"● 已匯入 {file_count} 檔，待映射",
                "quickstart-status-warn",
            )

        if file_count >= 2:
            self._set_quick_status(
                self._quick_status_reconcile,
                f"● 可對帳（{file_count} 檔）",
                "quickstart-status-ok",
            )
        else:
            self._set_quick_status(
                self._quick_status_reconcile,
                "● 對帳需至少 2 檔",
                "quickstart-status-warn",
            )

        if task_count > 0:
            self._set_quick_status(
                self._quick_status_task,
                f"● 已建任務 {task_count} 個",
                "quickstart-status-ok",
            )
        else:
            self._set_quick_status(
                self._quick_status_task,
                "● 尚未建立任務",
                "quickstart-status-muted",
            )

    @staticmethod
    def _set_quick_status(label: QLabel, text: str, role: str) -> None:
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)
        label.setText(text)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not hasattr(self, "_quick_btn_report"):
            return
        compact = self.width() < 1400
        min_w = 150 if compact else 170
        min_h = 64 if compact else 72
        for btn in (self._quick_btn_report, self._quick_btn_reconcile, self._quick_btn_task):
            btn.setMinimumWidth(min_w)
            btn.setMinimumHeight(min_h)
        self._refresh_quickstart_status()

    def _refresh_quickstart_status(self) -> None:
        if not hasattr(self, "_quick_status_report"):
            return
        files = len(self._controller.session.files)
        has_mapping = bool(self._controller.session.mapping)
        task_count = len(task_flows.list_flows())

        if files > 0 and has_mapping:
            self._set_quickstart_status(
                self._quick_status_report,
                f"● 產報就緒（{files} 檔）",
                "quickstart-status-ok",
            )
        elif files > 0:
            self._set_quickstart_status(
                self._quick_status_report,
                f"● 已匯入 {files} 檔，待映射",
                "quickstart-status-warn",
            )
        else:
            self._set_quickstart_status(
                self._quick_status_report,
                "● 尚未匯入檔案",
                "quickstart-status-muted",
            )

        if files >= 2:
            self._set_quickstart_status(
                self._quick_status_reconcile,
                f"● 可對帳（{files} 檔）",
                "quickstart-status-ok",
            )
        else:
            self._set_quickstart_status(
                self._quick_status_reconcile,
                "● 對帳需至少 2 檔",
                "quickstart-status-warn",
            )

        if task_count > 0:
            self._set_quickstart_status(
                self._quick_status_task,
                f"● 已建任務 {task_count} 個",
                "quickstart-status-ok",
            )
        else:
            self._set_quickstart_status(
                self._quick_status_task,
                "● 尚未建立任務",
                "quickstart-status-muted",
            )

    @staticmethod
    def _set_quickstart_status(label: QLabel, text: str, role: str) -> None:
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)
        label.setText(text)

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
        self._workflow.step_clicked.connect(self._on_workflow_step_clicked)

    def _bind_global_shortcuts(self) -> None:
        self._sc_add = QShortcut(QKeySequence("Ctrl+I"), self)
        self._sc_add.activated.connect(self._on_add_files)
        self._sc_task = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self._sc_task.activated.connect(self._on_task_flow_manager)
        self._sc_generate = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._sc_generate.activated.connect(self._on_generate)
        self._sc_preview = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self._sc_preview.activated.connect(self._on_preview)

    def _on_workflow_step_clicked(self, index: int) -> None:
        if index <= 0:
            self._preview.show_raw_tab()
            self._status.show_info("已切換到「原始」預覽。")
            return
        if index == 1:
            if self._controller.session.files:
                self._on_mapping()
            else:
                self._on_add_files()
            return
        if index == 2:
            self._on_validate()
            return
        if index == 3:
            self._on_preview()
            return
        self._on_generate()

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

    def _load_user_preferences(self) -> None:
        settings = QSettings()
        report_type_raw = settings.value(
            self._PREF_REPORT_TYPE,
            self._settings.report_type.report_type(),
        )
        report_type = str(report_type_raw) if report_type_raw is not None else "daily"
        if report_type not in {"daily", "weekly", "monthly"}:
            report_type = "daily"
        self._settings.report_type.set_report_type(report_type)  # type: ignore[arg-type]
        self._settings.date_range.set_report_type(report_type)  # type: ignore[arg-type]

        template_raw = settings.value(self._PREF_TEMPLATE, self._settings.template.template_path())
        template = str(template_raw) if template_raw is not None else ""
        if template:
            self._settings.template.set_template_path(template)
        else:
            self._settings.template.sync_to_report_type(report_type)  # type: ignore[arg-type]

        output_raw = settings.value(self._PREF_OUTPUT, self._settings.output.output_path())
        output = str(output_raw) if output_raw is not None else ""
        if output:
            self._settings.output.set_output_path(output)
        if bool(settings.value(self._PREF_HIGH_READABILITY, False, type=bool)):
            self._zoom.set_percent(max(110, int(round(self._zoom.factor() * 100))))

    def _show_onboarding_once(self) -> None:
        settings = QSettings()
        if bool(settings.value(self._PREF_ONBOARD_SEEN, False, type=bool)):
            return
        QMessageBox.information(
            self,
            "首次使用導覽",
            "歡迎使用！建議先從首頁卡片「② 匯入並對帳」開始。\n"
            "快捷鍵：Ctrl+I 匯入、Ctrl+Shift+P 預覽、Ctrl+Enter 產報。",
        )
        settings.setValue(self._PREF_ONBOARD_SEEN, True)

    def _on_toggle_high_readability(self, checked: bool) -> None:
        app = QApplication.instance()
        if app is None:
            return
        QSettings().setValue(self._PREF_HIGH_READABILITY, bool(checked))
        if checked:
            apply_theme(app, "bright_daylight")
            self._zoom.set_percent(max(110, int(round(self._zoom.factor() * 100))))
            self._status.show_info("已啟用高可讀模式。")
        else:
            self._status.show_info("已關閉高可讀模式。")

    def _save_user_pref(self, key: str, value: str) -> None:
        QSettings().setValue(key, value)

    def _current_date_spec(self) -> DateSpec:
        report_type: ReportType = self._settings.report_type.report_type()
        return self._settings.date_range.build_date_spec(report_type)

    # ------------------------------------------------------------------
    # File import (background)
    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        paths = self._pick_excel_files()
        if not paths:
            return
        self._import_paths([Path(p) for p in paths])

    def _pick_excel_files(self) -> list[str]:
        settings = QSettings()
        start_dir_raw = settings.value(self._PREF_LAST_OPEN_DIR, "")
        start_dir = str(start_dir_raw) if start_dir_raw else str(Path.home())

        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇 Excel 檔案",
            start_dir,
            "Excel (*.xlsx *.xls)",
        )
        if selected:
            settings.setValue(self._PREF_LAST_OPEN_DIR, str(Path(selected[0]).parent))
        return selected

    def _import_paths(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._sync_settings_to_controller()
        steps = import_file_steps(paths)
        self._run_with_steps(
            "import",
            steps,
            lambda tracker: self._controller.action_import_files(paths, tracker),
            self._finish_import,
        )

    @staticmethod
    def _extract_excel_paths(event: QDropEvent | QDragEnterEvent) -> list[Path]:
        if not event.mimeData().hasUrls():
            return []
        paths: list[Path] = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                paths.append(path)
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._tasks.is_busy:
            event.ignore()
            return
        if self._extract_excel_paths(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = self._extract_excel_paths(event)
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        self._import_paths(paths)
        self._log.append(f"已拖曳匯入 {len(paths)} 個 Excel 檔。", level="info")

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
        self._run_due_task_schedules()
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

    def _run_due_task_schedules(self) -> None:
        if self._tasks.is_busy:
            return
        due = task_flow_schedules.acquire_due_schedules(datetime.now())
        if not due:
            return
        flows = []
        continue_on_error = False
        for item in due:
            continue_on_error = continue_on_error or item.continue_on_error
            try:
                flow = task_flows.load_flow(item.flow_name)
            except (FileNotFoundError, ValueError) as exc:
                self._log.append(f"排程載入失敗：{item.flow_name}（{exc}）", level="error")
                continue
            if not flow.enabled:
                self._log.append(f"排程跳過停用任務：{flow.name}", level="warning")
                continue
            flows.append(flow)
        if not flows:
            return
        self._log.append(f"排程觸發：{len(flows)} 個任務開始執行。", level="info")
        runner = TaskFlowRunner(self._controller)

        def work() -> ActionResult:
            result = runner.run_many(
                flows,
                continue_on_error=continue_on_error,
            )
            for run in result.runs:
                task_flow_history.append_flow_run(asdict(run))
            return ActionResult(
                ok=result.ok,
                action="task_flow_schedule_runner",
                messages=result.messages,
                detail=f"排程已執行 {len(flows)} 個任務。",
                extra={
                    "outputs": result.outputs,
                    "failed_flow_name": result.failed_flow_name,
                    "failed_step_index": result.failed_step_index,
                    "failed_step_title": result.failed_step_title,
                },
            )

        self._run_background(
            "task_flow_schedule_runner",
            work,
            self._finish_scheduled_task_flow_runner,
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
        indices = self._settings.files.selected_indices()
        files = self._controller.session.files
        if not indices:
            self._log.append("請先選擇要移除的檔案。", level="warning")
            return
        chosen = [files[i] for i in indices if 0 <= i < len(files)]
        if not chosen:
            self._log.append("請先選擇要移除的檔案。", level="warning")
            return
        names = [item.path.name for item in chosen]
        for item in chosen:
            self._controller.remove_file(item.path)
        self._refresh_file_list()
        self._update_raw_preview()
        self._transformed_model.set_dataframe(self._controller.session.transformed_preview)
        if len(names) == 1:
            self._log.append(f"已移除：{names[0]}", level="info")
        else:
            self._log.append(f"已移除 {len(names)} 個檔案。", level="info")

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
        selected = self._settings.files.selected_indices()
        index = file_index if file_index is not None else (selected[0] if selected else -1)
        if index < 0 or index >= len(files):
            index = 0
        loaded = files[index]
        from app.core.mapping_utils import (
            remap_preset_for_file,
            storage_to_ui_mapping,
            ui_to_storage_mapping,
        )

        profile_suggestion = self._controller.suggest_mapping_profile(
            filename=loaded.path.name,
            source_columns=loaded.columns,
        )
        dialog = MappingDialog(
            source_columns=loaded.columns,
            current_mapping=storage_to_ui_mapping(
                self._controller.session.mapping,
                loaded.path.name,
            ),
            filename=loaded.path.name,
            profile_suggestion=profile_suggestion,
            parent=self,
        )
        if dialog.exec():
            ui_mapping = dialog.mapping()
            source_stored = ui_to_storage_mapping(ui_mapping, loaded.path.name)
            target_indices = (
                [i for i in selected if 0 <= i < len(files)]
                if file_index is None and len(selected) > 1
                else [index]
            )
            target_files = [files[i] for i in target_indices]
            merged = dict(self._controller.session.mapping)
            target_names = {item.path.name for item in target_files}
            merged = {
                key: val
                for key, val in merged.items()
                if key.split(":", 1)[0] not in target_names
            }
            applied = 0
            for item in target_files:
                remapped = remap_preset_for_file(
                    source_stored,
                    item.path.name,
                    item.columns,
                )
                if remapped:
                    merged.update(remapped)
                    applied += 1
            self._controller.set_mapping(merged)
            self._controller.remember_mapping_profile(
                filename=loaded.path.name,
                source_columns=loaded.columns,
                mapping_ui=ui_mapping,
            )
            self._refresh_session_ui(step=1)
            if len(target_files) <= 1:
                self._log.append(
                    f"「{loaded.path.name}」欄位映射已更新（{len(source_stored)} 項）。",
                    level="info",
                )
            else:
                skipped = len(target_files) - applied
                self._log.append(
                    f"已套用映射到 {applied} / {len(target_files)} 個檔案。"
                    + (f"（{skipped} 個檔案欄位不相容已略過）" if skipped else ""),
                    level="info",
                )

    def _on_range(self) -> None:
        files = self._controller.session.files
        selected = self._settings.files.selected_indices()
        index = selected[0] if selected else self._settings.files.selected_index()
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
        spec = dialog.range_spec()
        target_indices = [i for i in selected if 0 <= i < len(files)] if selected else [index]
        targets = [files[i] for i in target_indices]
        success = 0
        errors: list[str] = []
        for item in targets:
            r = self._controller.action_set_file_range(item.path, spec)
            if r.ok:
                success += 1
            else:
                errors.extend([m.message for m in r.messages if m.level == "error"])
        self._refresh_file_list()
        self._update_raw_preview()
        if errors:
            self._log.append("；".join(errors[:2]), level="error")
            if len(targets) == 1:
                QMessageBox.warning(self, "套用範圍失敗", errors[0])
        elif len(targets) == 1:
            self._log.append(f"已更新「{targets[0].path.name}」範圍。", level="info")
        if len(targets) > 1:
            self._log.append(
                f"已將範圍套用至 {success} / {len(targets)} 個檔案。",
                level="info",
            )

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

    def _build_current_setup(self) -> SetupPreset:
        report_type = self._settings.report_type.report_type()
        date_spec = self._settings.date_range.build_date_spec(report_type)
        return SetupPreset.from_runtime(
            name="",
            report_type=report_type,
            template_path=Path(self._settings.template.template_path()),
            output_dir=Path(self._settings.output.output_path()),
            date_spec=date_spec,
        )

    def _on_setup_runner(self) -> None:
        from app.ui.dialogs import SetupRunnerDialog

        dialog = SetupRunnerDialog(
            current_setup=self._build_current_setup(),
            parent=self,
        )
        if not dialog.exec():
            return
        mode = dialog.run_mode()
        if not mode:
            return
        if mode == "all":
            names = setup_presets.list_presets()
        else:
            names = dialog.selected_names()
        if not names:
            QMessageBox.information(self, "Setup 批次執行", "沒有可執行的 setup。")
            return

        setups: list[SetupPreset] = []
        for name in names:
            try:
                setups.append(setup_presets.load_preset(name))
            except (FileNotFoundError, ValueError) as exc:
                QMessageBox.warning(self, "載入 setup 失敗", str(exc))
                return

        original_type = self._controller.session.report_type
        original_output = self._controller.session.output_dir
        original_template = self._controller.session.template_path
        continue_on_error = dialog.continue_on_error()

        def work(tracker: ProcessTracker) -> ActionResult:
            messages: list[ValidationMessage] = []
            outputs: list[str] = []
            all_ok = True
            for idx, setup in enumerate(setups):
                tracker.start(idx, f"執行 setup：{setup.name}")
                self._controller.sync_session_settings(
                    report_type=setup.report_type,
                    output_dir=Path(setup.output_dir),
                    template_path=Path(setup.template_path),
                )
                if setup.filter_preset:
                    filter_result = self._controller.apply_filter_preset(setup.filter_preset)
                    messages.extend(filter_result.messages)
                    if filter_result.detail:
                        messages.append(
                            ValidationMessage(
                                level="info",
                                message=f"[{setup.name}] {filter_result.detail}",
                            )
                        )
                    if not filter_result.ok and not continue_on_error:
                        all_ok = False
                        tracker.done(idx)
                        break
                if setup.range_preset and self._controller.session.file_paths:
                    range_result = self._controller.apply_range_preset_to_paths(
                        setup.range_preset,
                        self._controller.session.file_paths,
                    )
                    messages.extend(range_result.messages)
                    if range_result.detail:
                        messages.append(
                            ValidationMessage(
                                level="info",
                                message=f"[{setup.name}] {range_result.detail}",
                            )
                        )
                    if not range_result.ok and not continue_on_error:
                        all_ok = False
                        tracker.done(idx)
                        break
                if setup.mapping_preset and self._controller.session.file_paths:
                    mapping_result = self._controller.apply_mapping_preset_to_paths(
                        setup.mapping_preset,
                        self._controller.session.file_paths,
                    )
                    messages.extend(mapping_result.messages)
                    if mapping_result.detail:
                        messages.append(
                            ValidationMessage(
                                level="info",
                                message=f"[{setup.name}] {mapping_result.detail}",
                            )
                        )
                    if not mapping_result.ok and not continue_on_error:
                        all_ok = False
                        tracker.done(idx)
                        break
                result = self._controller.action_generate(setup.to_date_spec())
                for msg in result.messages:
                    messages.append(
                        ValidationMessage(
                            level=msg.level,
                            message=f"[{setup.name}] {msg.message}",
                            source=msg.source,
                            code=msg.code,
                        )
                    )
                if result.ok and result.report_outcome and result.report_outcome.output_path:
                    outputs.append(str(result.report_outcome.output_path))
                if not result.ok:
                    all_ok = False
                    if not continue_on_error:
                        tracker.done(idx)
                        break
                tracker.done(idx)
            self._controller.sync_session_settings(
                report_type=original_type,
                output_dir=original_output,
                template_path=original_template,
            )
            detail = f"已完成 {len(outputs)} / {len(setups)} 個 setup。"
            return ActionResult(
                ok=all_ok,
                action="setup_runner",
                messages=messages,
                detail=detail,
                extra={"outputs": outputs},
            )

        self._run_with_steps(
            "setup_runner",
            [s.name for s in setups],
            work,
            self._finish_setup_runner,
        )

    def _on_task_flow_manager(self) -> None:
        from app.ui.task_flow_dialog import TaskFlowManagerDialog

        dialog = TaskFlowManagerDialog(
            current_setup=self._build_current_setup(),
            parent=self,
        )
        if not dialog.exec():
            return
        mode = dialog.run_mode()
        if not mode:
            return
        if mode == "all":
            names = task_flows.list_flows()
        else:
            names = dialog.selected_names()
        if not names:
            QMessageBox.information(self, "任務流程執行", "沒有可執行的任務。")
            return
        flows = []
        for name in names:
            try:
                flow = task_flows.load_flow(name)
            except (FileNotFoundError, ValueError) as exc:
                QMessageBox.warning(self, "載入任務失敗", str(exc))
                return
            if not flow.enabled:
                continue
            flows.append(flow)
        if not flows:
            QMessageBox.information(self, "任務流程執行", "選取任務皆為停用狀態。")
            return

        runner = TaskFlowRunner(self._controller)
        continue_on_error = dialog.continue_on_error()

        def work(tracker: ProcessTracker) -> ActionResult:
            result = runner.run_many(
                flows,
                continue_on_error=continue_on_error,
                on_flow_start=lambda idx, name: tracker.start(idx, f"執行任務：{name}"),
                on_flow_done=lambda idx, _name, _ok: tracker.done(idx),
            )
            for run in result.runs:
                task_flow_history.append_flow_run(asdict(run))
            detail = f"已完成 {len(result.outputs)} 份輸出，共執行 {len(flows)} 個任務。"
            return ActionResult(
                ok=result.ok,
                action="task_flow_runner",
                messages=result.messages,
                detail=detail,
                extra={
                    "outputs": result.outputs,
                    "failed_flow_name": result.failed_flow_name,
                    "failed_step_index": result.failed_step_index,
                    "failed_step_title": result.failed_step_title,
                },
            )

        self._run_with_steps(
            "task_flow_runner",
            [flow.name for flow in flows],
            work,
            self._finish_task_flow_runner,
        )

    def _finish_task_flow_runner(self, result: ActionResult) -> None:
        self._sync_settings_to_controller()
        outputs = [str(item) for item in result.extra.get("outputs", [])]
        if outputs:
            result.messages.append(
                ValidationMessage(
                    level="info",
                    message="輸出檔案：\n" + "\n".join(outputs),
                )
            )
        self._refresh_file_list()
        self._update_raw_preview()
        self._present_action_result(
            result,
            dialog_on_error=True,
            dialog_on_success=result.ok,
            success_title="任務流程執行完成",
        )
        if not result.ok:
            self._prompt_rerun_failed_step(result)
            self._offer_task_flow_fix(result)

    def _finish_scheduled_task_flow_runner(self, result: ActionResult) -> None:
        self._sync_settings_to_controller()
        outputs = [str(item) for item in result.extra.get("outputs", [])]
        if outputs:
            self._log.append("排程輸出：\n" + "\n".join(outputs), level="info")
        if result.ok:
            self._log.append(result.detail or "排程任務執行完成。", level="success")
        else:
            errors = [m.message for m in result.messages if m.level == "error"]
            self._log.append(
                "排程任務失敗：" + (errors[0] if errors else (result.detail or "未知錯誤")),
                level="error",
            )
            self._offer_task_flow_fix(result, interactive=False)

    def _offer_task_flow_fix(self, result: ActionResult, *, interactive: bool = True) -> None:
        errors = [m.message for m in result.messages if m.level == "error"]
        if not errors:
            return
        missing_preset = any(("preset" in msg and ("缺少" in msg or "找不到" in msg)) for msg in errors)
        if not missing_preset:
            return
        if not interactive:
            self._log.append("建議：開啟「任務流程管理」補齊缺少的 preset 設定。", level="warning")
            return
        answer = QMessageBox.question(
            self,
            "任務設定建議",
            "偵測到缺少 preset 設定。\n要立即開啟「任務流程管理」修正嗎？",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._on_task_flow_manager()

    def _prompt_rerun_failed_step(self, result: ActionResult) -> None:
        failed_flow = str(result.extra.get("failed_flow_name") or "").strip()
        failed_step = result.extra.get("failed_step_index")
        if not failed_flow or not isinstance(failed_step, int) or failed_step <= 0:
            return
        title = str(result.extra.get("failed_step_title") or f"第 {failed_step} 步")
        response = QMessageBox.question(
            self,
            "任務失敗",
            f"任務「{failed_flow}」失敗於 {title}。\n是否從該步驟重新執行？",
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        try:
            flow = task_flows.load_flow(failed_flow)
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "重跑失敗", str(exc))
            return
        runner = TaskFlowRunner(self._controller)

        def work(tracker: ProcessTracker) -> ActionResult:
            rerun = runner.run_many(
                [flow],
                continue_on_error=False,
                start_step_overrides={flow.name: failed_step},
                on_flow_start=lambda idx, name: tracker.start(idx, f"續跑任務：{name}"),
                on_flow_done=lambda idx, _name, _ok: tracker.done(idx),
            )
            for run in rerun.runs:
                task_flow_history.append_flow_run(asdict(run))
            return ActionResult(
                ok=rerun.ok,
                action="task_flow_rerun",
                messages=rerun.messages,
                detail=f"已從第 {failed_step} 步重新執行任務「{flow.name}」。",
                extra={
                    "outputs": rerun.outputs,
                    "failed_flow_name": rerun.failed_flow_name,
                    "failed_step_index": rerun.failed_step_index,
                    "failed_step_title": rerun.failed_step_title,
                },
            )

        self._run_with_steps(
            "task_flow_rerun",
            [f"{flow.name}（從第 {failed_step} 步）"],
            work,
            self._finish_task_flow_runner,
        )

    def _finish_setup_runner(self, result: ActionResult) -> None:
        self._sync_settings_to_controller()
        outputs = [str(item) for item in result.extra.get("outputs", [])]
        if outputs:
            result.messages.append(
                ValidationMessage(
                    level="info",
                    message="輸出檔案：\n" + "\n".join(outputs),
                )
            )
        self._present_action_result(
            result,
            dialog_on_error=True,
            dialog_on_success=result.ok,
            success_title="Setup 批次執行完成",
        )

    def _on_report_type_changed(self, report_type: str) -> None:
        self._controller.session.report_type = report_type  # type: ignore[assignment]
        self._save_user_pref(self._PREF_REPORT_TYPE, report_type)
        self._log.append(f"報表類型：{report_type}", level="info")

    def _on_template_changed(self, path: str) -> None:
        self._controller.session.template_path = Path(path)
        self._save_user_pref(self._PREF_TEMPLATE, str(path))
        self._log.append(f"範本：{Path(path).name}", level="info")

    def _on_output_path_changed(self, path: str) -> None:
        self._controller.session.output_dir = Path(path)
        self._save_user_pref(self._PREF_OUTPUT, str(path))
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
        # Failsafe: ensure button lock state always tracks runner state.
        self._set_busy(self._tasks.is_busy)

    def _on_task_failed(self, task_name: str, message: str) -> None:
        if self._process_dialog is not None:
            self._process_dialog.finish(False, message)
        self._log.append(f"[{task_name}] {message}", level="error")
        self._status.show_error("操作失敗")
        # Failsafe unlock if worker already ended.
        self._set_busy(self._tasks.is_busy)
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
        mapped_files = {key.split(":", 1)[0] for key in self._controller.session.mapping if ":" in key}
        items = []
        for f in self._controller.session.files:
            sheet = f.source_range.sheet or "-"
            mapped = "已映射" if f.path.name in mapped_files else "未映射"
            status = f"{sheet}｜{mapped}"
            items.append((f.path.name, f.row_count, f.range_summary(), status, str(f.path)))
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
