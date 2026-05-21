"""Task flow manager dialog (MVP)."""

from __future__ import annotations

import json
from datetime import date
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services import (
    filter_presets,
    setup_presets,
    task_flow_history,
    task_flow_schedules,
    task_flow_templates,
    task_flows,
)
from app.services.setup_presets import SetupPreset
from app.services.task_flows import TaskFlow, TaskFlowStep

ACTION_TEMPLATES: dict[str, dict[str, object]] = {
    "import": {
        "label": "匯入來源",
        "help": "從 files（指定檔案）或 folder（資料夾）匯入；兩者同時填時優先用 files。",
        "params": (
            ("files", "檔案清單（以 ; 或換行分隔）", r"C:\in\a.xlsx;C:\in\b.xlsx"),
            ("folder", "資料夾路徑", r"C:\inbox"),
            ("recursive", "遞迴（true/false）", "false"),
        ),
    },
    "apply_filter_preset": {
        "label": "套用檔名篩選 preset",
        "help": "先套用檔名篩選規則，後續匯入與流程會沿用這組設定。",
        "params": (("preset", "Preset 名稱", "my_filter"),),
    },
    "apply_range_preset": {
        "label": "套用範圍 preset",
        "help": "把欄位/列範圍設定套到目前已匯入檔案。",
        "params": (("preset", "Preset 名稱", "my_range"),),
    },
    "apply_mapping_preset": {
        "label": "套用映射 preset",
        "help": "將 canonical 欄位映射套到目前已匯入檔案。",
        "params": (("preset", "Preset 名稱", "my_mapping"),),
    },
    "validate": {"label": "驗證", "help": "檢查映射、日期與資料完整性。", "params": ()},
    "preview": {"label": "預覽", "help": "執行轉換並產生預覽，不輸出檔案。", "params": ()},
    "generate_report": {"label": "產生報表", "help": "正式產生報表檔案。", "params": ()},
    "clear_files": {"label": "清空檔案清單", "help": "清空目前工作階段已匯入檔案。", "params": ()},
    "reconcile": {
        "label": "資料對帳",
        "help": "比對兩檔共同欄位鍵與可選金額欄。left_file/right_file 可填檔名（工作階段內）或完整路徑。",
        "params": (
            ("left_file", "左檔（檔名或路徑）", "ledger.xlsx"),
            ("right_file", "右檔（檔名或路徑）", "system.xlsx"),
            ("key_columns", "對帳鍵（逗號分隔）", "日期,帳號"),
            ("amount_column", "金額欄（可留空）", "金額"),
            ("tolerance", "金額容差", "0.01"),
            ("output_name", "匯出檔名（可留空）", "reconcile_diff.xlsx"),
        ),
    },
}

FLOW_BLUEPRINTS: dict[str, tuple[tuple[str, str], ...]] = {
    "每日標準流程": (
        ("import", "匯入來源"),
        ("apply_filter_preset", "套用檔名篩選"),
        ("apply_range_preset", "套用範圍"),
        ("apply_mapping_preset", "套用映射"),
        ("validate", "驗證"),
        ("preview", "預覽"),
        ("generate_report", "產生報表"),
    ),
    "快速產報流程": (
        ("import", "匯入來源"),
        ("apply_mapping_preset", "套用映射"),
        ("generate_report", "產生報表"),
    ),
    "匯入後對帳": (
        ("import", "匯入來源"),
        ("reconcile", "雙邊對帳"),
    ),
}


class TaskFlowManagerDialog(QDialog):
    """Create/edit/delete task flow definitions."""

    def __init__(self, *, current_setup: SetupPreset, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("任務流程管理（MVP）")
        self.resize(980, 620)
        self._current_setup = current_setup
        self._selected_name: str | None = None
        self._step_items: list[TaskFlowStep] = []
        self._history_runs: list[dict[str, object]] = []
        self._param_inputs: dict[str, QLineEdit] = {}
        self._run_mode: str | None = None
        self._continue_on_error = True

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("已儲存任務"))
        self._flow_list = QListWidget()
        self._flow_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._flow_list.currentItemChanged.connect(self._on_flow_selected)
        left.addWidget(self._flow_list, stretch=1)
        left_actions = QHBoxLayout()
        self._new_btn = QPushButton("新增")
        self._new_btn.clicked.connect(self._on_new)
        self._wizard_btn = QPushButton("向導建立")
        self._wizard_btn.clicked.connect(self._on_wizard_create)
        self._delete_btn = QPushButton("刪除")
        self._delete_btn.clicked.connect(self._on_delete)
        self._export_btn = QPushButton("匯出")
        self._export_btn.clicked.connect(self._on_export)
        self._import_btn = QPushButton("匯入")
        self._import_btn.clicked.connect(self._on_import)
        left_actions.addWidget(self._new_btn)
        left_actions.addWidget(self._wizard_btn)
        left_actions.addWidget(self._delete_btn)
        left_actions.addWidget(self._export_btn)
        left_actions.addWidget(self._import_btn)
        left.addLayout(left_actions)
        left.addWidget(QLabel("最近執行紀錄"))
        history_filter = QHBoxLayout()
        self._history_keyword = QLineEdit()
        self._history_keyword.setPlaceholderText("搜尋關鍵字…")
        self._history_status = QComboBox()
        self._history_status.addItem("全部", "all")
        self._history_status.addItem("成功", "success")
        self._history_status.addItem("失敗", "failed")
        history_filter.addWidget(self._history_keyword, stretch=1)
        history_filter.addWidget(self._history_status)
        left.addLayout(history_filter)
        self._history_list = QListWidget()
        self._history_list.setMaximumHeight(170)
        self._history_list.itemDoubleClicked.connect(self._show_history_details)
        left.addWidget(self._history_list)
        history_btn = QPushButton("重新整理紀錄")
        history_btn.clicked.connect(lambda: self._refresh_history_list(self._selected_name))
        left.addWidget(history_btn)
        self._history_keyword.returnPressed.connect(
            lambda: self._refresh_history_list(self._selected_name)
        )
        self._history_status.currentIndexChanged.connect(
            lambda _idx: self._refresh_history_list(self._selected_name)
        )
        left.addWidget(QLabel("執行觀測"))
        self._obs_summary = QLabel("最近 50 次：無執行資料")
        self._obs_summary.setWordWrap(True)
        self._obs_summary.setProperty("role", "hint")
        left.addWidget(self._obs_summary)
        left.addWidget(QLabel("任務排程"))
        self._schedule_list = QListWidget()
        self._schedule_list.setMaximumHeight(150)
        left.addWidget(self._schedule_list)
        schedule_actions = QHBoxLayout()
        add_schedule_btn = QPushButton("新增排程")
        add_schedule_btn.clicked.connect(self._on_add_schedule)
        del_schedule_btn = QPushButton("刪除排程")
        del_schedule_btn.clicked.connect(self._on_delete_schedule)
        toggle_schedule_btn = QPushButton("啟用/停用")
        toggle_schedule_btn.clicked.connect(self._on_toggle_schedule)
        schedule_actions.addWidget(add_schedule_btn)
        schedule_actions.addWidget(del_schedule_btn)
        schedule_actions.addWidget(toggle_schedule_btn)
        left.addLayout(schedule_actions)
        root.addLayout(left, stretch=1)

        right_wrap = QWidget()
        right = QVBoxLayout(right_wrap)
        form = QFormLayout()
        self._name = QLineEdit()
        self._desc = QLineEdit()
        self._enabled = QCheckBox("啟用此任務")
        self._enabled.setChecked(True)
        self._tags = QLineEdit()
        self._resources = QTextEdit()
        self._resources.setPlaceholderText('{"source_folder":"...", "template_path":"...", "output_dir":"..."}')
        self._resources.setMaximumHeight(120)
        form.addRow("任務名稱：", self._name)
        form.addRow("描述：", self._desc)
        form.addRow("標籤（逗號）：", self._tags)
        form.addRow("", self._enabled)
        form.addRow("資源參數（JSON）：", self._resources)
        setup_row = QHBoxLayout()
        self._setup_combo = QComboBox()
        self._setup_combo.addItem("（由 setup 建立任務）", "")
        setup_row.addWidget(self._setup_combo, stretch=1)
        setup_build_btn = QPushButton("載入 setup 成為任務")
        setup_build_btn.clicked.connect(self._build_from_setup)
        setup_row.addWidget(setup_build_btn)
        setup_wrap = QWidget()
        setup_wrap.setLayout(setup_row)
        form.addRow("setup 快速轉換：", setup_wrap)
        right.addLayout(form)

        right.addWidget(QLabel("流程步驟"))
        self._steps = QListWidget()
        self._steps.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._steps.model().rowsMoved.connect(self._sync_steps_from_widget_order)
        self._steps.currentRowChanged.connect(self._on_step_selected)
        right.addWidget(self._steps, stretch=1)

        step_actions = QHBoxLayout()
        for text, fn in (
            ("新增步驟", self._add_step),
            ("刪除步驟", self._remove_step),
            ("上移", self._move_step_up),
            ("下移", self._move_step_down),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            step_actions.addWidget(btn)
        right.addLayout(step_actions)

        flow_blueprint_row = QHBoxLayout()
        flow_blueprint_row.addWidget(QLabel("常見流程："))
        self._blueprint_combo = QComboBox()
        self._blueprint_combo.addItem("（選擇流程模板）", "")
        for name in FLOW_BLUEPRINTS:
            self._blueprint_combo.addItem(name, name)
        flow_blueprint_row.addWidget(self._blueprint_combo, stretch=1)
        apply_blueprint_btn = QPushButton("插入流程")
        apply_blueprint_btn.clicked.connect(self._insert_blueprint_steps)
        flow_blueprint_row.addWidget(apply_blueprint_btn)
        right.addLayout(flow_blueprint_row)

        step_editor = QFormLayout()
        self._step_title = QLineEdit()
        self._step_action = QComboBox()
        self._step_action.setEditable(True)
        self._step_action.addItem("（選擇動作模板）", "")
        for action, info in ACTION_TEMPLATES.items():
            label = str(info.get("label", action))
            self._step_action.addItem(f"{label}（{action}）", action)
        self._step_action.currentIndexChanged.connect(self._on_step_action_changed)
        step_editor.addRow("步驟標題：", self._step_title)
        step_editor.addRow("步驟動作：", self._step_action)
        right.addLayout(step_editor)
        self._action_help = QLabel("選擇步驟動作後，這裡會顯示說明。")
        self._action_help.setWordWrap(True)
        right.addWidget(self._action_help)

        self._param_form = QFormLayout()
        self._param_form_wrap = QWidget()
        self._param_form_wrap.setLayout(self._param_form)
        right.addWidget(QLabel("步驟參數（表單）"))
        right.addWidget(self._param_form_wrap)
        right.addWidget(QLabel("其他參數（每行 key=value，可留空）"))
        self._extra_params = QTextEdit()
        self._extra_params.setMaximumHeight(90)
        self._extra_params.setPlaceholderText("例如：\nsource_folder=C:\\inbox\ntrade_date=2026-05-20")
        right.addWidget(self._extra_params)
        self._apply_step_btn = QPushButton("套用目前步驟設定")
        self._apply_step_btn.clicked.connect(self._apply_step_editor)
        right.addWidget(self._apply_step_btn)

        self._continue = QCheckBox("遇錯繼續後續任務（建議開啟）")
        self._continue.setChecked(True)
        right.addWidget(self._continue)

        footer = QHBoxLayout()
        run_selected_btn = QPushButton("執行選取任務")
        run_selected_btn.clicked.connect(self._on_run_selected)
        run_all_btn = QPushButton("執行全部任務")
        run_all_btn.clicked.connect(self._on_run_all)
        self._save_btn = QPushButton("儲存任務")
        self._save_btn.clicked.connect(self._save_flow)
        footer.addWidget(run_selected_btn)
        footer.addWidget(run_all_btn)
        footer.addStretch()
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(self._save_btn)
        footer.addWidget(close_btn)
        right.addLayout(footer)
        root.addWidget(right_wrap, stretch=2)

        self._refresh_flow_list()
        self._refresh_setup_combo()
        self._refresh_history_list()
        self._refresh_schedule_list()
        self._load_from_flow(self._default_flow("新任務"))

    def _default_flow(self, name: str) -> TaskFlow:
        return task_flow_templates.flow_from_setup(name, self._current_setup)

    def _refresh_flow_list(self) -> None:
        self._flow_list.clear()
        for name in task_flows.list_flows():
            self._flow_list.addItem(QListWidgetItem(name))

    def _refresh_setup_combo(self) -> None:
        self._setup_combo.clear()
        self._setup_combo.addItem("（由 setup 建立任務）", "")
        for name in setup_presets.list_presets():
            self._setup_combo.addItem(name, name)

    def _build_from_setup(self) -> None:
        setup_name = str(self._setup_combo.currentData() or "").strip()
        if not setup_name:
            QMessageBox.information(self, "setup 轉任務", "請先選擇 setup。")
            return
        try:
            setup = setup_presets.load_preset(setup_name)
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "載入 setup 失敗", str(exc))
            return
        task_name = f"{setup.name}_task"
        self._selected_name = None
        self._load_from_flow(task_flow_templates.flow_from_setup(task_name, setup))

    def _on_new(self) -> None:
        name, ok = QInputDialog.getText(self, "新增任務", "任務名稱：")
        if not ok or not name.strip():
            return
        self._selected_name = None
        self._load_from_flow(self._default_flow(name.strip()))

    def _on_wizard_create(self) -> None:
        name, ok = QInputDialog.getText(self, "建立任務向導（1/4）", "任務名稱：")
        if not ok or not name.strip():
            return
        folder = QFileDialog.getExistingDirectory(self, "建立任務向導（2/4）- 選擇資料夾", "")
        if not folder:
            return
        presets = ["（不套用）"] + filter_presets.list_presets()
        chosen_preset, ok = QInputDialog.getItem(
            self,
            "建立任務向導（3/4）",
            "關鍵字篩選 preset：",
            presets,
            editable=False,
        )
        if not ok:
            return
        template_path, _ = QFileDialog.getOpenFileName(
            self,
            "建立任務向導（4/4）- 選擇範本",
            self._current_setup.template_path,
            "Excel (*.xlsx)",
        )
        if not template_path:
            return
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "建立任務向導（4/4）- 選擇輸出資料夾",
            self._current_setup.output_dir,
        )
        if not output_dir:
            return
        setup = SetupPreset(
            name=name.strip(),
            report_type=self._current_setup.report_type,
            template_path=template_path,
            output_dir=output_dir,
            trade_date=self._current_setup.trade_date,
            week_start=self._current_setup.week_start,
            week_end=self._current_setup.week_end,
            month=self._current_setup.month,
            mapping_preset=None,
            range_preset=None,
            filter_preset=(None if chosen_preset == "（不套用）" else chosen_preset),
        )
        flow = task_flow_templates.flow_from_setup(name.strip(), setup)
        steps = []
        for step in flow.steps:
            if step.action == "import":
                steps.append(
                    TaskFlowStep(
                        id=step.id,
                        action=step.action,
                        title=step.title,
                        params={"folder": folder, "recursive": "true"},
                    )
                )
            else:
                steps.append(step)
        self._selected_name = None
        self._load_from_flow(
            TaskFlow(
                task_id=flow.task_id,
                name=flow.name,
                description="向導建立：資料夾掃描 + 關鍵字篩選 + 產報",
                version=flow.version,
                enabled=flow.enabled,
                tags=flow.tags,
                resources=flow.resources,
                steps=tuple(steps),
            )
        )

    def _on_delete(self) -> None:
        item = self._flow_list.currentItem()
        if item is None:
            QMessageBox.information(self, "刪除任務", "請先選擇任務。")
            return
        name = item.text()
        if (
            QMessageBox.question(self, "刪除任務", f"確定刪除「{name}」？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        task_flows.delete_flow(name)
        self._refresh_flow_list()
        self._selected_name = None
        self._load_from_flow(self._default_flow("新任務"))

    def _on_flow_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self._refresh_history_list()
            return
        name = current.text().strip()
        if not name:
            self._refresh_history_list()
            return
        try:
            flow = task_flows.load_flow(name)
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "載入任務失敗", str(exc))
            return
        self._selected_name = name
        self._load_from_flow(flow)
        self._refresh_history_list(name)

    def _load_from_flow(self, flow: TaskFlow) -> None:
        self._name.setText(flow.name)
        self._desc.setText(flow.description)
        self._enabled.setChecked(flow.enabled)
        self._tags.setText(", ".join(flow.tags))
        self._resources.setPlainText(json.dumps(flow.resources, ensure_ascii=False, indent=2))
        self._step_items = list(flow.steps)
        self._refresh_step_list()
        self._clear_step_editor()

    def _refresh_step_list(self) -> None:
        self._steps.clear()
        for idx, step in enumerate(self._step_items, start=1):
            item = QListWidgetItem(f"{idx}. {step.title} ({step.action})")
            item.setData(Qt.ItemDataRole.UserRole, step.id)
            self._steps.addItem(item)

    def _on_step_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._step_items):
            self._clear_step_editor()
            return
        step = self._step_items[row]
        self._step_title.setText(step.title)
        action_idx = self._step_action.findData(step.action)
        if action_idx >= 0:
            self._step_action.setCurrentIndex(action_idx)
        else:
            self._step_action.setCurrentIndex(-1)
            self._step_action.setEditText(step.action)
        self._update_action_help(step.action)
        self._rebuild_param_form(step.action, step.params)

    def _apply_step_editor(self) -> None:
        row = self._steps.currentRow()
        if row < 0 or row >= len(self._step_items):
            return
        action = self._current_action().strip()
        title = self._step_title.text().strip()
        if not action:
            QMessageBox.warning(self, "步驟設定", "請設定步驟動作。")
            return
        if not title:
            title = action
        params, error = self._collect_editor_params()
        if error:
            QMessageBox.warning(self, "步驟參數格式錯誤", error)
            return
        validate_error = self._validate_step_params(action, params)
        if validate_error:
            QMessageBox.warning(self, "步驟參數檢查", validate_error)
            return
        self._step_items[row] = replace(
            self._step_items[row],
            title=title,
            action=action,
            params=params,
        )
        self._refresh_step_list()
        self._steps.setCurrentRow(row)

    def _add_step(self) -> None:
        options = [f"{v['label']}（{k}）" for k, v in ACTION_TEMPLATES.items()]
        choice, ok = QInputDialog.getItem(self, "新增步驟", "選擇步驟模板：", options, editable=False)
        if not ok or not choice:
            return
        action = next(
            (k for k, v in ACTION_TEMPLATES.items() if choice.startswith(str(v["label"]))),
            "",
        )
        if not action:
            return
        step = TaskFlowStep(
            id=uuid4().hex[:8],
            action=action,
            title=str(ACTION_TEMPLATES[action]["label"]),
            params={},
        )
        self._step_items.append(step)
        self._refresh_step_list()
        self._steps.setCurrentRow(len(self._step_items) - 1)

    def _insert_blueprint_steps(self) -> None:
        raw = self._blueprint_combo.currentData()
        name = str(raw or "").strip()
        if not name:
            QMessageBox.information(self, "流程模板", "請先選擇要插入的流程模板。")
            return
        blueprint = FLOW_BLUEPRINTS.get(name)
        if not blueprint:
            return
        if self._step_items:
            resp = QMessageBox.question(
                self,
                "流程模板",
                "目前已有步驟，是否改為附加在尾端？\n按「否」將覆蓋現有步驟。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if resp == QMessageBox.StandardButton.Cancel:
                return
            if resp == QMessageBox.StandardButton.No:
                self._step_items = []
        self._step_items.extend(
            task_flow_templates.build_blueprint_steps(
                blueprint,
                current_setup=self._current_setup,
            )
        )
        self._refresh_step_list()
        self._steps.setCurrentRow(len(self._step_items) - 1)

    def _remove_step(self) -> None:
        row = self._steps.currentRow()
        if row < 0 or row >= len(self._step_items):
            return
        self._step_items.pop(row)
        self._refresh_step_list()
        self._steps.setCurrentRow(min(row, len(self._step_items) - 1))

    def _move_step_up(self) -> None:
        row = self._steps.currentRow()
        if row <= 0 or row >= len(self._step_items):
            return
        self._step_items[row - 1], self._step_items[row] = self._step_items[row], self._step_items[row - 1]
        self._refresh_step_list()
        self._steps.setCurrentRow(row - 1)

    def _move_step_down(self) -> None:
        row = self._steps.currentRow()
        if row < 0 or row >= len(self._step_items) - 1:
            return
        self._step_items[row + 1], self._step_items[row] = self._step_items[row], self._step_items[row + 1]
        self._refresh_step_list()
        self._steps.setCurrentRow(row + 1)

    def _save_flow(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "儲存任務", "任務名稱不可為空。")
            return
        tags = tuple(item.strip() for item in self._tags.text().split(",") if item.strip())
        try:
            resources_raw = json.loads(self._resources.toPlainText().strip() or "{}")
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "資源參數格式錯誤", str(exc))
            return
        if not isinstance(resources_raw, dict):
            QMessageBox.warning(self, "資源參數格式錯誤", "資源參數必須是 JSON 物件。")
            return
        task_id = uuid4().hex
        if self._selected_name is not None:
            try:
                task_id = task_flows.load_flow(self._selected_name).task_id
            except (FileNotFoundError, ValueError):
                task_id = uuid4().hex
        flow = TaskFlow(
            task_id=task_id,
            name=name,
            description=self._desc.text().strip(),
            version=1,
            enabled=self._enabled.isChecked(),
            tags=tags,
            resources={str(k): str(v) for k, v in resources_raw.items()},
            steps=tuple(self._step_items),
        )
        try:
            path = task_flows.save_flow(flow)
        except ValueError as exc:
            QMessageBox.warning(self, "儲存失敗", str(exc))
            return
        self._selected_name = name
        self._refresh_flow_list()
        self._focus_flow_name(name)
        QMessageBox.information(self, "已儲存", f"任務已儲存至：\n{path}")

    def _on_export(self) -> None:
        names = self.selected_names()
        if not names:
            if self._selected_name:
                names = [self._selected_name]
            else:
                QMessageBox.information(self, "匯出任務", "請先選擇至少一個任務。")
                return
        default_name = "task_flows_export.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出任務",
            default_name,
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            saved = task_flows.export_flows(names, Path(path))
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "匯出失敗", str(exc))
            return
        QMessageBox.information(self, "匯出完成", f"已匯出 {len(names)} 個任務：\n{saved}")

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入任務",
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        overwrite = (
            QMessageBox.question(
                self,
                "匯入任務",
                "遇到同名任務時要覆蓋嗎？\n是＝覆蓋，否＝略過同名。",
            )
            == QMessageBox.StandardButton.Yes
        )
        try:
            imported, skipped = task_flows.import_flows(Path(path), overwrite=overwrite)
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "匯入失敗", str(exc))
            return
        self._refresh_flow_list()
        self._refresh_setup_combo()
        QMessageBox.information(
            self,
            "匯入完成",
            f"已匯入 {imported} 個任務，略過 {skipped} 個任務。",
        )

    def _on_run_selected(self) -> None:
        if not self.selected_names():
            QMessageBox.information(self, "執行任務", "請先在左側選擇至少一個任務。")
            return
        self._continue_on_error = self._continue.isChecked()
        self._run_mode = "selected"
        self.accept()

    def _on_run_all(self) -> None:
        if not task_flows.list_flows():
            QMessageBox.information(self, "執行任務", "目前沒有可執行的任務。")
            return
        self._continue_on_error = self._continue.isChecked()
        self._run_mode = "all"
        self.accept()

    def _focus_flow_name(self, name: str) -> None:
        for idx in range(self._flow_list.count()):
            item = self._flow_list.item(idx)
            if item and item.text() == name:
                self._flow_list.setCurrentRow(idx)
                return

    def _refresh_history_list(self, flow_name: str | None = None) -> None:
        self._history_list.clear()
        self._history_runs = []
        runs = task_flow_history.list_recent_runs(
            limit=20,
            flow_name=flow_name,
            keyword=self._history_keyword.text(),
            status=str(self._history_status.currentData() or "all"),
        )
        if not runs:
            self._history_list.addItem("（尚無執行紀錄）")
            return
        self._history_runs = runs
        for run in runs:
            self._history_list.addItem(task_flow_history.summarize_run(run))
        self._refresh_observability()

    def _refresh_observability(self) -> None:
        runs = task_flow_history.list_recent_runs(limit=50, flow_name=self._selected_name)
        if not runs:
            self._obs_summary.setText("最近 50 次：無執行資料")
            return
        total = len(runs)
        success = sum(1 for item in runs if bool(item.get("ok", False)))
        avg_ms = int(sum(int(item.get("duration_ms", 0) or 0) for item in runs) / max(total, 1))
        success_rate = (success / total) * 100
        self._obs_summary.setText(
            f"最近 {total} 次：成功 {success} 次（{success_rate:.1f}%）\n"
            f"平均耗時：{avg_ms} ms"
        )

    def _refresh_schedule_list(self) -> None:
        self._schedule_list.clear()
        items = task_flow_schedules.list_schedules()
        if not items:
            self._schedule_list.addItem("（尚無排程）")
            return
        for item in items:
            weekdays = ",".join(str(w) for w in item.weekdays) if item.weekdays else "-"
            mode = "每日" if item.mode == "daily" else f"每週({weekdays})"
            state = "啟用" if item.enabled else "停用"
            self._schedule_list.addItem(
                f"{item.schedule_id[:8]} | {item.flow_name} | {mode} {item.time_hhmm} | {state}"
            )

    def _selected_schedule_id(self) -> str:
        item = self._schedule_list.currentItem()
        if item is None:
            return ""
        text = item.text().strip()
        if "|" not in text:
            return ""
        return text.split("|", 1)[0].strip()

    def _on_add_schedule(self) -> None:
        flow_names = task_flows.list_flows()
        if not flow_names:
            QMessageBox.information(self, "新增排程", "請先至少建立一個任務流程。")
            return
        flow, ok = QInputDialog.getItem(self, "新增排程", "任務流程：", flow_names, editable=False)
        if not ok or not flow:
            return
        mode_label, ok = QInputDialog.getItem(
            self,
            "新增排程",
            "排程模式：",
            ["每日", "每週"],
            editable=False,
        )
        if not ok:
            return
        hhmm, ok = QInputDialog.getText(self, "新增排程", "執行時間（HH:MM，24小時）：", text="09:00")
        if not ok:
            return
        weekdays: tuple[int, ...] = ()
        mode = "daily" if mode_label == "每日" else "weekly"
        if mode == "weekly":
            text, ok = QInputDialog.getText(
                self,
                "新增排程",
                "星期（0-6, 0=週一；可逗號，例如 0,1,2,3,4）：",
                text="0,1,2,3,4",
            )
            if not ok:
                return
            parts = [item.strip() for item in text.split(",") if item.strip()]
            try:
                weekdays = tuple(sorted({int(part) for part in parts if 0 <= int(part) <= 6}))
            except ValueError:
                QMessageBox.warning(self, "新增排程", "星期格式錯誤，請輸入 0-6。")
                return
        try:
            schedule = task_flow_schedules.create_schedule(
                flow_name=str(flow),
                mode=mode,
                time_hhmm=hhmm,
                weekdays=weekdays,
            )
            task_flow_schedules.save_schedule(schedule)
        except ValueError as exc:
            QMessageBox.warning(self, "新增排程", str(exc))
            return
        self._refresh_schedule_list()

    def _on_delete_schedule(self) -> None:
        sid8 = self._selected_schedule_id()
        if not sid8:
            QMessageBox.information(self, "刪除排程", "請先選擇排程。")
            return
        full = next(
            (item.schedule_id for item in task_flow_schedules.list_schedules() if item.schedule_id.startswith(sid8)),
            "",
        )
        if not full:
            return
        task_flow_schedules.delete_schedule(full)
        self._refresh_schedule_list()

    def _on_toggle_schedule(self) -> None:
        sid8 = self._selected_schedule_id()
        if not sid8:
            QMessageBox.information(self, "啟用/停用排程", "請先選擇排程。")
            return
        schedules = task_flow_schedules.list_schedules()
        for item in schedules:
            if not item.schedule_id.startswith(sid8):
                continue
            updated = task_flow_schedules.TaskSchedule(
                schedule_id=item.schedule_id,
                flow_name=item.flow_name,
                mode=item.mode,
                time_hhmm=item.time_hhmm,
                weekdays=item.weekdays,
                enabled=not item.enabled,
                continue_on_error=item.continue_on_error,
                last_trigger_key=item.last_trigger_key,
            )
            task_flow_schedules.save_schedule(updated)
            break
        self._refresh_schedule_list()

    def _show_history_details(self, *_args) -> None:
        row = self._history_list.currentRow()
        if row < 0 or row >= len(self._history_runs):
            return
        run = self._history_runs[row]
        text = task_flow_history.run_details_text(run)
        dialog = QDialog(self)
        dialog.setWindowTitle("任務執行明細")
        dialog.resize(760, 520)
        layout = QVBoxLayout(dialog)
        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText(text)
        layout.addWidget(box, stretch=1)
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def _sync_steps_from_widget_order(self, *_args) -> None:
        if not self._step_items:
            return
        by_id = {step.id: step for step in self._step_items}
        ordered: list[TaskFlowStep] = []
        for idx in range(self._steps.count()):
            item = self._steps.item(idx)
            if item is None:
                continue
            step_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
            step = by_id.get(step_id)
            if step is not None:
                ordered.append(step)
        if len(ordered) == len(self._step_items):
            self._step_items = ordered
            self._refresh_step_list()

    @staticmethod
    def _validate_step_params(action: str, params: dict[str, str]) -> str | None:
        if action == "import":
            files = params.get("files", "").strip()
            folder = params.get("folder", "").strip()
            if not files and not folder:
                return "import 步驟至少需要 files 或 folder 其中一項。"
            recursive = params.get("recursive", "").strip().lower()
            if recursive and recursive not in {"true", "false"}:
                return "recursive 僅接受 true 或 false。"
        if action in {"apply_filter_preset", "apply_range_preset", "apply_mapping_preset"}:
            if not params.get("preset", "").strip():
                return f"{action} 需要 preset 名稱。"
        if action == "reconcile":
            if not params.get("left_file", "").strip():
                return "reconcile 需要 left_file（檔名或路徑）。"
            if not params.get("right_file", "").strip():
                return "reconcile 需要 right_file（檔名或路徑）。"
            if not params.get("key_columns", "").strip():
                return "reconcile 需要 key_columns（逗號分隔）。"
            tolerance = params.get("tolerance", "").strip()
            if tolerance:
                try:
                    float(tolerance)
                except ValueError:
                    return "tolerance 需為數字。"
        for key in ("trade_date", "week_start", "week_end", "month"):
            value = params.get(key, "").strip()
            if not value:
                continue
            try:
                date.fromisoformat(value)
            except ValueError:
                return f"{key} 需為 YYYY-MM-DD 格式。"
        return None

    def _on_step_action_changed(self) -> None:
        row = self._steps.currentRow()
        action = self._current_action()
        self._update_action_help(action)
        if row < 0 or row >= len(self._step_items):
            return
        params = self._step_items[row].params
        self._rebuild_param_form(action, params)

    def _current_action(self) -> str:
        data = self._step_action.currentData()
        if data:
            return str(data)
        return self._step_action.currentText().strip()

    def _clear_step_editor(self) -> None:
        self._step_title.clear()
        self._step_action.setCurrentIndex(0)
        self._extra_params.clear()
        self._update_action_help("")
        self._rebuild_param_form("", {})

    def _update_action_help(self, action: str) -> None:
        info = ACTION_TEMPLATES.get(action, {})
        label = str(info.get("label", action or "未選擇"))
        help_text = str(info.get("help", "可直接輸入自訂 action 與參數。"))
        self._action_help.setText(f"【{label}】{help_text}")

    def _rebuild_param_form(self, action: str, params: dict[str, str]) -> None:
        while self._param_form.rowCount():
            self._param_form.removeRow(0)
        self._param_inputs.clear()
        left = dict(params)
        template = ACTION_TEMPLATES.get(action, {})
        template_params = template.get("params", ())
        if isinstance(template_params, tuple):
            for item in template_params:
                key, label, placeholder = item
                entry = QLineEdit()
                entry.setPlaceholderText(str(placeholder))
                entry.setText(left.pop(str(key), ""))
                self._param_form.addRow(f"{label}：", entry)
                self._param_inputs[str(key)] = entry
        if left:
            self._extra_params.setPlainText(
                "\n".join(f"{k}={v}" for k, v in left.items() if str(k).strip())
            )
        else:
            self._extra_params.clear()

    def _collect_editor_params(self) -> tuple[dict[str, str], str | None]:
        params: dict[str, str] = {}
        for key, editor in self._param_inputs.items():
            value = editor.text().strip()
            if value:
                params[key] = value
        extra = self._extra_params.toPlainText().strip()
        if not extra:
            return params, None
        for raw in extra.splitlines():
            line = raw.strip()
            if not line:
                continue
            if "=" not in line:
                return {}, f"參數格式錯誤：{line}（需為 key=value）"
            key, value = line.split("=", 1)
            k = key.strip()
            if not k:
                return {}, f"參數鍵不可為空：{line}"
            params[k] = value.strip()
        return params, None

    def run_mode(self) -> str | None:
        return self._run_mode

    def selected_names(self) -> list[str]:
        return [item.text() for item in self._flow_list.selectedItems() if item.text().strip()]

    def continue_on_error(self) -> bool:
        return self._continue_on_error
