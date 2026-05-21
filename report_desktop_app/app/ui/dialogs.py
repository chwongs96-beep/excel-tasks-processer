"""Modal dialogs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableView,
    QTextBrowser,
    QVBoxLayout,
)

from app.core import config
from app.core.mapping_utils import (
    remap_preset_for_file,
    storage_to_ui_mapping,
    ui_to_storage_mapping,
)
from app.core.range_spec import SourceRangeSpec
from app.core.schemas import LoadedFile
from app.services import filter_presets, mapping_presets, range_presets, setup_presets
from app.services.excel_reader import ExcelReaderService
from app.services.batch_report_service import BatchReportRequest, dates_in_range
from app.services.setup_presets import SetupPreset
from app.services.smart_profile_service import ProfileSuggestion
from app.services.smart_mapping_advisor import MappingSuggestion
from app.services.smart_mapping_advisor import from_config as advisor_from_config
from app.services.reconcile_hints import suggest_amount_column, suggest_key_columns
from app.services.reconcile_service import ReconcileRequest
from app.ui.help_text import RECONCILE_HELP_HTML
from app.ui.table_model import DataFrameTableModel
from app.ui.ui_utils import hint_label, set_tooltip, wrap_help_html


class AboutDialog(QDialog):
    """Simple about box."""

    def __init__(self, app_name: str, version: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("關於")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{app_name}\n版本 {version}\n\n內部證券會計報表工具"))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MappingDialog(QDialog):
    """Map Excel column headers to canonical field names."""

    def __init__(
        self,
        *,
        source_columns: list[str],
        current_mapping: dict[str, str],
        filename: str,
        profile_suggestion: ProfileSuggestion | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("欄位映射")
        self.resize(560, 440)
        self._filename = filename
        self._source_columns = list(source_columns)
        self._mapping: dict[str, str] = dict(current_mapping)
        self._combos: dict[str, QComboBox] = {}
        self._suggestions: dict[str, MappingSuggestion] = {}
        self._profile_suggestion = profile_suggestion

        schema = config.load_schema_config()
        canonical_names = list(schema.canonical_fields)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"檔案：{filename}\n"
                "為每個標準欄位選擇對應的 Excel 欄位；留空表示略過（將嘗試別名自動對應）。"
            )
        )

        self._build_preset_row(layout)
        self._build_profile_row(layout)
        self._build_advisor_row(layout)
        self._build_smart_apply_row(layout)

        form = QFormLayout()
        for field in canonical_names:
            combo = QComboBox()
            combo.addItem("（不映射）", "")
            for col in source_columns:
                combo.addItem(col, col)
            selected = self._mapping.get(field, "")
            index = combo.findData(selected)
            combo.setCurrentIndex(index if index >= 0 else 0)
            form.addRow(f"{field}：", combo)
            self._combos[field] = combo

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_preset_row(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel("映射 preset："))

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("（選擇 preset）", "")
        for name in mapping_presets.list_presets():
            self._preset_combo.addItem(name, name)
        row.addWidget(self._preset_combo, stretch=1)

        load_btn = QPushButton("載入")
        load_btn.clicked.connect(self._on_load_preset)
        row.addWidget(load_btn)

        save_btn = QPushButton("儲存…")
        save_btn.clicked.connect(self._on_save_preset)
        row.addWidget(save_btn)

        layout.addLayout(row)

    def _build_profile_row(self, layout: QVBoxLayout) -> None:
        if not self._profile_suggestion:
            return
        row = QHBoxLayout()
        apply_btn = QPushButton("套用歷史設定")
        apply_btn.clicked.connect(self._on_apply_profile)
        row.addWidget(apply_btn)
        confidence = int(round(self._profile_suggestion.confidence * 100))
        row.addWidget(
            hint_label(
                f"歷史建議：{len(self._profile_suggestion.mapping)} 項（信心 {confidence}%）"
                f"｜{self._profile_suggestion.reason}"
            ),
            stretch=1,
        )
        layout.addLayout(row)

    def _on_apply_profile(self) -> None:
        if not self._profile_suggestion:
            return
        self._mapping = self._merge_candidates(self._mapping, self._profile_suggestion.mapping)
        self._apply_mapping_to_combos()

    def _build_advisor_row(self, layout: QVBoxLayout) -> None:
        mode_cfg = config.load_smart_mode_config()
        if not bool(mode_cfg.get("enabled", True)):
            return
        try:
            advisor = advisor_from_config()
            self._suggestions = advisor.suggest(source_columns=self._source_columns)
        except Exception:  # noqa: BLE001
            self._suggestions = {}

        row = QHBoxLayout()
        apply_btn = QPushButton("套用智慧建議")
        apply_btn.clicked.connect(self._on_apply_suggestions)
        apply_btn.setEnabled(bool(self._suggestions))
        row.addWidget(apply_btn)
        n_total = len(self._suggestions)
        n_auto = sum(
            1
            for item in self._suggestions.values()
            if item.score >= float(mode_cfg.get("advisor", {}).get("auto_apply_threshold", 0.85))
        )
        tip = (
            f"智慧建議：{n_total} 項（高信心 {n_auto} 項）"
            if n_total
            else "智慧建議：目前欄位無明確對應"
        )
        row.addWidget(hint_label(tip), stretch=1)
        layout.addLayout(row)

    def _on_apply_suggestions(self) -> None:
        if not self._suggestions:
            QMessageBox.information(self, "智慧建議", "目前沒有可套用的映射建議。")
            return
        candidates = {field: item.source_column for field, item in self._suggestions.items()}
        self._mapping = self._merge_candidates(self._mapping, candidates)
        self._apply_mapping_to_combos()

    def _build_smart_apply_row(self, layout: QVBoxLayout) -> None:
        candidates = self._smart_candidates()
        if not candidates:
            return
        conflict_count = len(self._smart_conflicts())
        row = QHBoxLayout()
        apply_btn = QPushButton("一鍵智能套用")
        apply_btn.clicked.connect(self._on_apply_smart)
        row.addWidget(apply_btn)
        if conflict_count:
            msg = f"衝突 {conflict_count} 項（優先採用歷史設定）"
        else:
            msg = "歷史與智慧建議已整合"
        row.addWidget(hint_label(msg), stretch=1)
        layout.addLayout(row)
        if conflict_count:
            self._conflict_list = QListWidget()
            self._conflict_list.setProperty("role", "conflict-list")
            self._conflict_list.setMaximumHeight(120)
            self._conflict_list.setAlternatingRowColors(True)
            for field, (profile_col, advisor_col) in self._smart_conflicts().items():
                self._conflict_list.addItem(
                    f"{field}: 歷史「{profile_col}」 / 智慧「{advisor_col}」"
                )
            layout.addWidget(
                hint_label("衝突清單：一鍵智能套用時，會先採用歷史設定。")
            )
            layout.addWidget(self._conflict_list)

    def _on_apply_smart(self) -> None:
        candidates = self._smart_candidates()
        if not candidates:
            QMessageBox.information(self, "智能套用", "目前沒有可套用的建議。")
            return
        self._mapping = self._merge_candidates(self._mapping, candidates)
        self._apply_mapping_to_combos()

    def _smart_candidates(self) -> dict[str, str]:
        merged: dict[str, str] = {}
        if self._profile_suggestion:
            merged.update(self._profile_suggestion.mapping)
        for field, suggestion in self._suggestions.items():
            merged.setdefault(field, suggestion.source_column)
        return merged

    def _smart_conflicts(self) -> dict[str, tuple[str, str]]:
        if not self._profile_suggestion or not self._suggestions:
            return {}
        conflicts: dict[str, tuple[str, str]] = {}
        for field, profile_col in self._profile_suggestion.mapping.items():
            advisor = self._suggestions.get(field)
            if advisor and advisor.source_column != profile_col:
                conflicts[field] = (profile_col, advisor.source_column)
        return conflicts

    @staticmethod
    def _merge_candidates(base: dict[str, str], candidates: dict[str, str]) -> dict[str, str]:
        """Merge mapping without overriding user-set fields or duplicating source columns."""
        result = dict(base)
        used_sources = {source for source in result.values() if source}
        for field, source in candidates.items():
            if not source:
                continue
            if result.get(field):
                continue
            if source in used_sources:
                continue
            result[field] = source
            used_sources.add(source)
        return result

    def _on_load_preset(self) -> None:
        name = self._preset_combo.currentData()
        if not name:
            QMessageBox.information(self, "載入 preset", "請先選擇要載入的 preset。")
            return
        try:
            preset = mapping_presets.load_preset(str(name))
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "載入失敗", str(exc))
            return

        stored = remap_preset_for_file(preset, self._filename, self._source_columns)
        if not stored:
            QMessageBox.warning(
                self,
                "載入 preset",
                "此 preset 的欄位名稱與目前檔案欄位不符，無法套用。",
            )
            return

        self._mapping = storage_to_ui_mapping(stored, self._filename)
        self._apply_mapping_to_combos()

    def _on_save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "儲存 preset", "Preset 名稱：")
        if not ok or not name.strip():
            return
        stored = ui_to_storage_mapping(self.mapping(), self._filename)
        if not stored:
            QMessageBox.warning(self, "儲存 preset", "請至少映射一個欄位。")
            return
        try:
            path = mapping_presets.save_preset(name.strip(), stored)
        except ValueError as exc:
            QMessageBox.warning(self, "儲存失敗", str(exc))
            return
        QMessageBox.information(self, "已儲存", f"已儲存至：\n{path}")
        self._refresh_preset_list(name.strip())

    def _refresh_preset_list(self, select_name: str) -> None:
        self._preset_combo.clear()
        self._preset_combo.addItem("（選擇 preset）", "")
        for preset_name in mapping_presets.list_presets():
            self._preset_combo.addItem(preset_name, preset_name)
        index = self._preset_combo.findData(select_name)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)

    def _apply_mapping_to_combos(self) -> None:
        for field, combo in self._combos.items():
            selected = self._mapping.get(field, "")
            index = combo.findData(selected)
            combo.setCurrentIndex(index if index >= 0 else 0)

    def mapping(self) -> dict[str, str]:
        """Canonical field -> Excel column name (empty entries omitted)."""
        result: dict[str, str] = {}
        for field, combo in self._combos.items():
            value = combo.currentData()
            if value:
                result[field] = str(value)
        return result


class SetupRunnerDialog(QDialog):
    """Manage saved setups and choose selected/all execution mode."""

    def __init__(self, *, current_setup: SetupPreset, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setup 批次執行")
        self.resize(620, 460)
        self._current_setup = current_setup
        self._run_mode: str | None = None
        self._continue_on_error = True

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "可先儲存目前設定，再選擇執行單一 setup 或全部依序執行。"
                "（第一版：序列執行）"
            )
        )

        row = QHBoxLayout()
        self._name_edit = QLineEdit(current_setup.name or "")
        self._name_edit.setPlaceholderText("輸入 setup 名稱（例如：日報_台股）")
        row.addWidget(self._name_edit, stretch=1)
        save_btn = QPushButton("儲存目前設定")
        save_btn.clicked.connect(self._on_save_current)
        row.addWidget(save_btn)
        layout.addLayout(row)

        preset_form = QFormLayout()
        self._mapping_combo = QComboBox()
        self._mapping_combo.addItem("（不綁定）", "")
        for name in mapping_presets.list_presets():
            self._mapping_combo.addItem(name, name)
        if current_setup.mapping_preset:
            idx = self._mapping_combo.findData(current_setup.mapping_preset)
            if idx >= 0:
                self._mapping_combo.setCurrentIndex(idx)
        preset_form.addRow("mapping preset：", self._mapping_combo)

        self._range_combo = QComboBox()
        self._range_combo.addItem("（不綁定）", "")
        for name in range_presets.list_presets():
            self._range_combo.addItem(name, name)
        if current_setup.range_preset:
            idx = self._range_combo.findData(current_setup.range_preset)
            if idx >= 0:
                self._range_combo.setCurrentIndex(idx)
        preset_form.addRow("range preset：", self._range_combo)

        self._filter_combo = QComboBox()
        self._filter_combo.addItem("（不綁定）", "")
        for name in filter_presets.list_presets():
            self._filter_combo.addItem(name, name)
        if current_setup.filter_preset:
            idx = self._filter_combo.findData(current_setup.filter_preset)
            if idx >= 0:
                self._filter_combo.setCurrentIndex(idx)
        preset_form.addRow("filter preset：", self._filter_combo)
        layout.addLayout(preset_form)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list, stretch=1)

        self._continue = QCheckBox("遇錯繼續後續 setup（建議開啟）")
        self._continue.setChecked(True)
        layout.addWidget(self._continue)

        actions = QHBoxLayout()
        del_btn = QPushButton("刪除選取")
        del_btn.clicked.connect(self._on_delete_selected)
        actions.addWidget(del_btn)
        actions.addStretch()

        run_one = QPushButton("執行選取")
        run_one.clicked.connect(self._on_run_selected)
        actions.addWidget(run_one)
        run_all = QPushButton("全部依序執行")
        run_all.clicked.connect(self._on_run_all)
        actions.addWidget(run_all)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        layout.addLayout(actions)

        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        for name in setup_presets.list_presets():
            item = QListWidgetItem(name)
            self._list.addItem(item)

    def _on_save_current(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "儲存 setup", "請先輸入 setup 名稱。")
            return
        preset = SetupPreset(
            name=name,
            report_type=self._current_setup.report_type,
            template_path=self._current_setup.template_path,
            output_dir=self._current_setup.output_dir,
            trade_date=self._current_setup.trade_date,
            week_start=self._current_setup.week_start,
            week_end=self._current_setup.week_end,
            month=self._current_setup.month,
            mapping_preset=str(self._mapping_combo.currentData() or "") or None,
            range_preset=str(self._range_combo.currentData() or "") or None,
            filter_preset=str(self._filter_combo.currentData() or "") or None,
        )
        try:
            path = setup_presets.save_preset(preset)
        except ValueError as exc:
            QMessageBox.warning(self, "儲存失敗", str(exc))
            return
        QMessageBox.information(self, "已儲存", f"已儲存至：\n{path}")
        self._refresh_list()

    def _on_delete_selected(self) -> None:
        names = self.selected_names()
        if not names:
            QMessageBox.information(self, "刪除 setup", "請先選擇至少一個 setup。")
            return
        if QMessageBox.question(
            self,
            "刪除 setup",
            f"確定刪除 {len(names)} 個 setup？",
        ) != QMessageBox.StandardButton.Yes:
            return
        for name in names:
            setup_presets.delete_preset(name)
        self._refresh_list()

    def _on_run_selected(self) -> None:
        if not self.selected_names():
            QMessageBox.information(self, "執行 setup", "請先選擇至少一個 setup。")
            return
        self._continue_on_error = self._continue.isChecked()
        self._run_mode = "selected"
        self.accept()

    def _on_run_all(self) -> None:
        if not setup_presets.list_presets():
            QMessageBox.information(self, "執行 setup", "目前沒有可執行的 setup。")
            return
        self._continue_on_error = self._continue.isChecked()
        self._run_mode = "all"
        self.accept()

    def run_mode(self) -> str | None:
        return self._run_mode

    def selected_names(self) -> list[str]:
        return [item.text() for item in self._list.selectedItems() if item.text().strip()]

    def continue_on_error(self) -> bool:
        return self._continue_on_error


class RangeSelectionDialog(QDialog):
    """Pick sheet and cell range before copy/merge, with live preview."""

    def __init__(
        self,
        *,
        path: Path,
        sheet_names: list[str],
        current: SourceRangeSpec | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"資料範圍 — {path.name}")
        self.resize(720, 560)
        self._path = path
        self._reader = ExcelReaderService()
        self._spec = current or SourceRangeSpec.default()

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "指定要複製的區域。標題列用於欄位名稱；亦可直接輸入 Excel 範圍（例如 B2:H500）。"
                "變更後請按「預覽範圍」確認標題與資料是否正確。"
            )
        )

        self._build_preset_row(layout)

        form = QFormLayout()
        self._sheet = QComboBox()
        for name in sheet_names or ["Sheet1"]:
            self._sheet.addItem(name, name)
        if self._spec.sheet:
            idx = self._sheet.findData(self._spec.sheet)
            if idx >= 0:
                self._sheet.setCurrentIndex(idx)

        self._header_row = QSpinBox()
        self._header_row.setRange(1, 1_000_000)
        self._header_row.setValue(self._spec.header_row)

        self._start_row = QSpinBox()
        self._start_row.setRange(0, 1_000_000)
        self._start_row.setSpecialValueText("（自動）")
        self._start_row.setValue(self._spec.start_row or 0)

        self._end_row = QSpinBox()
        self._end_row.setRange(0, 1_000_000)
        self._end_row.setSpecialValueText("（至末列）")
        self._end_row.setValue(self._spec.end_row or 0)

        self._excel_range = QLineEdit()
        self._excel_range.setPlaceholderText("選填，例如 A2:H500（優先於列號）")
        if self._spec.excel_range:
            self._excel_range.setText(self._spec.excel_range)

        form.addRow("工作表：", self._sheet)
        form.addRow("標題列：", self._header_row)
        form.addRow("資料起始列：", self._start_row)
        form.addRow("資料結束列：", self._end_row)
        form.addRow("Excel 範圍：", self._excel_range)
        layout.addLayout(form)

        preview_row = QHBoxLayout()
        preview_btn = QPushButton("預覽範圍")
        preview_btn.clicked.connect(self._refresh_preview)
        preview_row.addWidget(preview_btn)
        self._clear_btn = QPushButton("清除此範圍內容…")
        self._clear_btn.setToolTip(
            "清除目前指定範圍內所有儲存格的值（直接寫回此檔案，無法復原）。"
        )
        self._clear_btn.clicked.connect(self._on_clear_range)
        preview_row.addWidget(self._clear_btn)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        self._preview_caption = QLabel("尚未預覽")
        layout.addWidget(self._preview_caption)
        self._preview_model = DataFrameTableModel()
        self._preview_view = QTableView()
        self._preview_view.setModel(self._preview_model)
        self._preview_view.setAlternatingRowColors(True)
        self._preview_view.horizontalHeader().setStretchLastSection(True)
        self._preview_view.setMaximumHeight(220)
        layout.addWidget(self._preview_view)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_preview()

    def _build_preset_row(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel("範圍 preset："))
        self._range_preset_combo = QComboBox()
        self._range_preset_combo.addItem("（選擇 preset）", "")
        for name in range_presets.list_presets():
            self._range_preset_combo.addItem(name, name)
        row.addWidget(self._range_preset_combo, stretch=1)
        load_btn = QPushButton("載入")
        load_btn.clicked.connect(self._on_load_range_preset)
        row.addWidget(load_btn)
        save_btn = QPushButton("儲存…")
        save_btn.clicked.connect(self._on_save_range_preset)
        row.addWidget(save_btn)
        layout.addLayout(row)

    def _apply_spec_to_form(self, spec: SourceRangeSpec) -> None:
        if spec.sheet:
            idx = self._sheet.findData(spec.sheet)
            if idx >= 0:
                self._sheet.setCurrentIndex(idx)
        self._header_row.setValue(spec.header_row)
        self._start_row.setValue(spec.start_row or 0)
        self._end_row.setValue(spec.end_row or 0)
        self._excel_range.setText(spec.excel_range or "")

    def _on_load_range_preset(self) -> None:
        name = self._range_preset_combo.currentData()
        if not name:
            QMessageBox.information(self, "載入 preset", "請先選擇要載入的範圍 preset。")
            return
        try:
            spec = range_presets.load_preset(str(name))
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "載入失敗", str(exc))
            return
        self._apply_spec_to_form(spec)
        self._refresh_preview()

    def _on_save_range_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "儲存範圍 preset", "Preset 名稱（例如：券商A_成交明細）：")
        if not ok or not name.strip():
            return
        try:
            path = range_presets.save_preset(name.strip(), self.range_spec())
        except ValueError as exc:
            QMessageBox.warning(self, "儲存失敗", str(exc))
            return
        QMessageBox.information(self, "已儲存", f"已儲存至：\n{path}")
        self._range_preset_combo.clear()
        self._range_preset_combo.addItem("（選擇 preset）", "")
        for preset_name in range_presets.list_presets():
            self._range_preset_combo.addItem(preset_name, preset_name)
        idx = self._range_preset_combo.findData(name.strip())
        if idx >= 0:
            self._range_preset_combo.setCurrentIndex(idx)

    def _on_clear_range(self) -> None:
        spec = self.range_spec()
        reply = QMessageBox.warning(
            self,
            "清除範圍內容",
            f"將清除下列範圍內所有儲存格的值，並<strong>直接儲存</strong>至：\n"
            f"{self._path.name}\n\n"
            f"範圍：{spec.summary()}\n\n"
            "此操作無法復原，是否繼續？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.services.excel_clear_service import ExcelClearService

        result = ExcelClearService().clear_range(self._path, spec)
        if result.success:
            QMessageBox.information(self, "已清除", result.message)
            self._refresh_preview()
        else:
            QMessageBox.warning(self, "清除失敗", result.error or "未知錯誤")

    def _refresh_preview(self) -> None:
        try:
            spec = self.range_spec()
            frame = self._reader.load_sheet(self._path, range_spec=spec).head(
                config.DIALOG_PREVIEW_ROWS
            )
        except Exception as exc:  # noqa: BLE001
            self._preview_model.set_dataframe(None)
            self._preview_caption.setText(f"預覽失敗：{exc}")
            return
        self._preview_model.set_dataframe(frame)
        rows_note = f"顯示前 {len(frame)} 列"
        self._preview_caption.setText(
            f"預覽 — {spec.summary()}（{rows_note}，共 {len(frame.columns)} 欄）"
        )

    def range_spec(self) -> SourceRangeSpec:
        excel_range = self._excel_range.text().strip() or None
        start_row = self._start_row.value() or None
        end_row = self._end_row.value() or None
        return SourceRangeSpec(
            sheet=self._sheet.currentData(),
            header_row=self._header_row.value(),
            start_row=start_row,
            end_row=end_row,
            excel_range=excel_range,
        )


class ReconcileDialog(QDialog):
    """Professional two-file reconciliation with help and key suggestions."""

    def __init__(
        self,
        files: list[LoadedFile],
        *,
        output_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("資料對帳 — 雙邊比對")
        self.resize(680, 620)
        self._files = files
        self._output_dir = Path(output_dir)

        root = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_help_tab(), "① 說明與原理")
        self._tabs.addTab(self._build_setup_tab(), "② 對帳設定")
        root.addWidget(self._tabs)

        self._meta = QLabel()
        self._meta.setProperty("role", "caption")
        root.addWidget(self._meta)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("執行對帳")
        buttons.accepted.connect(self._validate_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._left.currentIndexChanged.connect(self._refresh_columns)
        self._right.currentIndexChanged.connect(self._refresh_columns)
        self._amount_col.currentIndexChanged.connect(self._update_mode_hint)
        self._refresh_columns()

    def _build_help_tab(self) -> QWidget:
        from PySide6.QtWidgets import QWidget

        page = QWidget()
        layout = QVBoxLayout(page)
        browser = QTextBrowser()
        browser.setHtml(wrap_help_html(RECONCILE_HELP_HTML))
        layout.addWidget(browser)
        return page

    def _build_setup_tab(self) -> QWidget:
        from PySide6.QtWidgets import QWidget

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(
            hint_label(
                "左檔通常為基準（券商／銀行明細），右檔為比對對象（系統／總帳匯出）。"
                "兩邊須已設定正確的「資料範圍」。"
            )
        )

        form = QFormLayout()
        self._left = QComboBox()
        self._right = QComboBox()
        for loaded in self._files:
            label = f"{loaded.path.name}（{loaded.row_count:,} 列）"
            self._left.addItem(label, loaded)
            self._right.addItem(label, loaded)
        if self._left.count() > 1:
            self._right.setCurrentIndex(1)
        form.addRow("左檔（基準／來源 A）：", self._left)
        form.addRow("右檔（比對／來源 B）：", self._right)
        layout.addLayout(form)

        suggest_row = QHBoxLayout()
        suggest_btn = QPushButton("套用建議對帳鍵")
        suggest_btn.clicked.connect(self._apply_suggested_keys)
        set_tooltip(suggest_btn, "依欄位名稱與標準 schema 別名，自動勾選常見對帳鍵。")
        suggest_row.addWidget(suggest_btn)
        clear_btn = QPushButton("清除勾選")
        clear_btn.clicked.connect(self._clear_keys)
        suggest_row.addWidget(clear_btn)
        suggest_row.addStretch()
        layout.addLayout(suggest_row)

        layout.addWidget(QLabel("對帳鍵欄位（可多選，組合成一筆交易的唯一識別）："))
        self._key_list = QListWidget()
        self._key_list.setMinimumHeight(140)
        layout.addWidget(self._key_list)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        key_form = QFormLayout()
        self._amount_col = QComboBox()
        self._amount_col.addItem("（不比對金額，僅比對鍵是否存在）", "")
        key_form.addRow("金額欄（選填）：", self._amount_col)

        self._tolerance = QDoubleSpinBox()
        self._tolerance.setRange(0.0, 1_000_000.0)
        self._tolerance.setDecimals(4)
        self._tolerance.setValue(0.01)
        self._tolerance.setSuffix(" 元")
        set_tooltip(
            self._tolerance,
            "兩邊鍵相同時，若 |左−右| 大於此值，列為「金額不符」。",
        )
        key_form.addRow("金額容差：", self._tolerance)
        layout.addLayout(key_form)

        self._export = QCheckBox(
            "匯出對帳報告（Excel 三個工作表：僅左邊、僅右邊、金額不符）"
        )
        self._export.setChecked(True)
        layout.addWidget(self._export)

        self._mode_hint = hint_label(
            "對帳模式：僅比對鍵是否存在（未選金額欄）。"
            " 對帳鍵使用兩檔「共同欄位名」（非映射後欄位）。"
        )
        self._mode_hint.setWordWrap(True)
        layout.addWidget(self._mode_hint)
        return page

    def _loaded(self, combo: QComboBox) -> LoadedFile:
        return combo.currentData()

    def _refresh_columns(self) -> None:
        left = self._loaded(self._left)
        right = self._loaded(self._right)
        common = sorted(set(left.columns) & set(right.columns))
        self._key_list.clear()
        for col in common:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._key_list.addItem(item)

        self._amount_col.clear()
        self._amount_col.addItem("（不比對金額，僅比對鍵是否存在）", "")
        for col in common:
            self._amount_col.addItem(col, col)

        amount = suggest_amount_column(list(common))
        self._apply_suggested_keys()

        self._meta.setText(
            f"左：{left.path.name}（{left.range_summary()}）｜"
            f"右：{right.path.name}（{right.range_summary()}）｜"
            f"共同欄位 {len(common)} 個"
            + (f"｜建議金額欄：{amount}" if amount else "")
        )
        if amount:
            idx = self._amount_col.findData(amount)
            if idx < 0:
                idx = self._amount_col.findText(amount)
            if idx >= 0:
                self._amount_col.setCurrentIndex(idx)

        suggested = suggest_key_columns(left.columns, right.columns)
        if len(common) < 2:
            self._meta.setStyleSheet("color: #b45309;")
        elif not suggested:
            self._meta.setStyleSheet("color: #b45309;")
        else:
            self._meta.setStyleSheet("")
        self._update_mode_hint()

    def _update_mode_hint(self) -> None:
        amount = self._amount_col.currentData() or ""
        if amount:
            self._mode_hint.setText(
                f"對帳模式：鍵相符時比對金額欄「{amount}」（容差 {self._tolerance.value():g}）。"
                " 對帳鍵使用兩檔「共同欄位名」（非映射後欄位）。"
            )
        else:
            self._mode_hint.setText(
                "對帳模式：僅比對鍵是否存在（未選金額欄，不會產生「金額不符」）。"
                " 對帳鍵使用兩檔「共同欄位名」（非映射後欄位）。"
            )

    def _selected_keys(self) -> list[str]:
        keys: list[str] = []
        for index in range(self._key_list.count()):
            item = self._key_list.item(index)
            if item and item.checkState() == Qt.CheckState.Checked:
                keys.append(item.text())
        return keys

    def _validate_accept(self) -> None:
        left = self._loaded(self._left)
        right = self._loaded(self._right)
        if left.path.resolve() == right.path.resolve():
            QMessageBox.warning(
                self,
                "資料對帳",
                "左右檔案不可相同。\n請選擇兩個不同的 Excel 來源。",
            )
            return

        common = sorted(set(left.columns) & set(right.columns))
        if len(common) < 1:
            QMessageBox.warning(
                self,
                "資料對帳",
                "兩檔沒有任何共同欄位名稱，無法對帳。\n\n"
                "建議：\n"
                "1. 確認兩檔已設定正確「資料範圍」與標題列\n"
                "2. 先統一欄名（合併或手動調整 Excel 標題）\n"
                "3. 再重新匯入後執行對帳",
            )
            return

        keys = self._selected_keys()
        if not keys:
            QMessageBox.warning(self, "資料對帳", "請至少勾選一個對帳鍵欄位。")
            return

        suggested = suggest_key_columns(left.columns, right.columns)
        if len(common) < 2 or not suggested:
            guide = (
                "共同欄位偏少或無法自動建議對帳鍵。\n"
                "請確認兩檔標題列一致，或手動勾選能唯一識別交易的欄位組合。"
            )
            if (
                QMessageBox.warning(
                    self,
                    "對帳鍵提示",
                    guide + "\n\n仍要繼續執行對帳嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return

        amount = self._amount_col.currentData() or ""
        if not amount:
            if (
                QMessageBox.information(
                    self,
                    "僅存在性比對",
                    "未選擇金額欄：本次只比對「鍵是否存在」（僅左／僅右），"
                    "不會產生「金額不符」結果。\n\n確定要繼續嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return

        self.accept()

    def _apply_suggested_keys(self) -> None:
        left = self._loaded(self._left)
        right = self._loaded(self._right)
        suggested = set(suggest_key_columns(left.columns, right.columns))
        for index in range(self._key_list.count()):
            item = self._key_list.item(index)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked if item.text() in suggested else Qt.CheckState.Unchecked
                )

    def _clear_keys(self) -> None:
        for index in range(self._key_list.count()):
            item = self._key_list.item(index)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def build_request(self) -> ReconcileRequest | None:
        left = self._loaded(self._left)
        right = self._loaded(self._right)
        keys: list[str] = []
        for index in range(self._key_list.count()):
            item = self._key_list.item(index)
            if item and item.checkState() == Qt.CheckState.Checked:
                keys.append(item.text())
        if not keys:
            return None

        amount = self._amount_col.currentData() or None
        output_path = None
        if self._export.isChecked():
            output_path = self._output_dir / f"reconcile_{left.path.stem}_vs_{right.path.stem}.xlsx"

        return ReconcileRequest(
            left_path=left.path,
            right_path=right.path,
            left_range=left.source_range,
            right_range=right.source_range,
            key_columns=keys,
            amount_column=str(amount) if amount else None,
            tolerance=self._tolerance.value(),
            output_path=output_path,
        )


class BatchReportDialog(QDialog):
    """Generate daily reports for each date in a range."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("批次產生日報")
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("依序為區間內每個日期產生一份日報（輸出至目前輸出資料夾）。"))

        form = QFormLayout()
        self._start = QDateEdit(calendarPopup=True)
        self._end = QDateEdit(calendarPopup=True)
        for widget in (self._start, self._end):
            widget.setDisplayFormat("yyyy-MM-dd")
        today = QDate.currentDate()
        self._end.setDate(today)
        self._start.setDate(today.addDays(-4))
        form.addRow("起始日期：", self._start)
        form.addRow("結束日期：", self._end)
        layout.addLayout(form)

        self._weekdays_only = QCheckBox("僅工作日（週一至週五）")
        self._weekdays_only.setChecked(True)
        layout.addWidget(self._weekdays_only)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def build_request(
        self,
        *,
        files: list[Path],
        mapping: dict[str, str],
        output_dir: Path,
        template_path: Path | None,
    ) -> BatchReportRequest:
        start = self._qdate_to_date(self._start.date())
        end = self._qdate_to_date(self._end.date())
        return BatchReportRequest(
            report_type="daily",
            dates=dates_in_range(
                start,
                end,
                business_days_only=self._weekdays_only.isChecked(),
            ),
            files=files,
            mapping=mapping,
            output_dir=output_dir,
            template_path=template_path,
        )

    @staticmethod
    def _qdate_to_date(qdate: QDate) -> date:
        return date(qdate.year(), qdate.month(), qdate.day())


class FolderWatchDialog(QDialog):
    """Pick a folder, filter by filename keywords, preview matches, optional watch."""

    def __init__(
        self,
        current: Path | None = None,
        *,
        initial_filter=None,
        parent=None,
    ) -> None:
        from app.core.file_name_filter import FileNameFilter
        from app.services import filter_presets, range_presets

        super().__init__(parent)
        self.setWindowTitle("智慧資料夾匯入")
        self.resize(560, 520)

        self._filter = initial_filter or FileNameFilter.empty()
        self._last_scan = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "選擇資料夾後，依<strong>檔名關鍵字</strong>篩選要匯入的 Excel。"
                "可儲存規則 preset，並選擇自動套用範圍 preset。"
            )
        )

        row = QHBoxLayout()
        self._path_edit = QLineEdit(str(current or ""))
        browse = QPushButton("瀏覽…")
        browse.clicked.connect(self._browse)
        row.addWidget(self._path_edit)
        row.addWidget(browse)
        layout.addLayout(row)

        self._recursive = QCheckBox("包含子資料夾")
        layout.addWidget(self._recursive)

        kw_form = QFormLayout()
        self._include_edit = QLineEdit()
        self._include_edit.setPlaceholderText("逗號分隔，例如：成交, TDCC（留空＝全部）")
        self._exclude_edit = QLineEdit()
        self._exclude_edit.setPlaceholderText("例如：draft, 備份, temp")
        self._case_insensitive = QCheckBox("不分大小寫")
        self._case_insensitive.setChecked(True)
        kw_form.addRow("包含關鍵字：", self._include_edit)
        kw_form.addRow("排除關鍵字：", self._exclude_edit)
        kw_form.addRow("", self._case_insensitive)
        layout.addLayout(kw_form)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("關鍵字 preset："))
        self._filter_preset_combo = QComboBox()
        self._filter_preset_combo.addItem("（選擇 preset）", "")
        for name in filter_presets.list_presets():
            self._filter_preset_combo.addItem(name, name)
        preset_row.addWidget(self._filter_preset_combo, stretch=1)
        load_fp = QPushButton("載入")
        load_fp.clicked.connect(self._load_filter_preset)
        save_fp = QPushButton("儲存…")
        save_fp.clicked.connect(self._save_filter_preset)
        preset_row.addWidget(load_fp)
        preset_row.addWidget(save_fp)
        layout.addLayout(preset_row)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("匯入後套用範圍："))
        self._range_preset_combo = QComboBox()
        self._range_preset_combo.addItem("（不套用）", "")
        for name in range_presets.list_presets():
            self._range_preset_combo.addItem(name, name)
        range_row.addWidget(self._range_preset_combo, stretch=1)
        layout.addLayout(range_row)

        preview_btn = QPushButton("預覽符合檔案")
        preview_btn.clicked.connect(self._refresh_preview)
        layout.addWidget(preview_btn)

        self._preview_label = QLabel("尚未預覽")
        self._preview_label.setProperty("role", "caption")
        layout.addWidget(self._preview_label)

        self._preview_list = QListWidget()
        self._preview_list.setMaximumHeight(140)
        layout.addWidget(self._preview_list)

        self._enable_watch = QCheckBox("啟用監看（新檔依相同關鍵字規則自動匯入，每 60 秒）")
        layout.addWidget(self._enable_watch)

        self._apply_filter_to_form(self._filter)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("匯入符合的檔案")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_filter_to_form(self, rules) -> None:
        from app.core.file_name_filter import FileNameFilter

        rules = rules or FileNameFilter.empty()
        self._include_edit.setText(", ".join(rules.include_any))
        self._exclude_edit.setText(", ".join(rules.exclude_any))
        self._case_insensitive.setChecked(rules.case_insensitive)
        if rules.range_preset:
            idx = self._range_preset_combo.findData(rules.range_preset)
            if idx >= 0:
                self._range_preset_combo.setCurrentIndex(idx)

    def _parse_filter(self):
        from app.core.file_name_filter import FileNameFilter

        def _split(text: str) -> tuple[str, ...]:
            parts = [p.strip() for p in text.replace(";", ",").split(",")]
            return tuple(p for p in parts if p)

        range_name = self._range_preset_combo.currentData() or None
        return FileNameFilter(
            include_any=_split(self._include_edit.text()),
            exclude_any=_split(self._exclude_edit.text()),
            case_insensitive=self._case_insensitive.isChecked(),
            range_preset=str(range_name) if range_name else None,
        )

    def _load_filter_preset(self) -> None:
        from app.services import filter_presets

        name = self._filter_preset_combo.currentData()
        if not name:
            QMessageBox.information(self, "載入 preset", "請先選擇關鍵字 preset。")
            return
        try:
            rules = filter_presets.load_preset(str(name))
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "載入失敗", str(exc))
            return
        self._apply_filter_to_form(rules)
        self._refresh_preview()

    def _save_filter_preset(self) -> None:
        from app.services import filter_presets

        name, ok = QInputDialog.getText(
            self,
            "儲存關鍵字 preset",
            "Preset 名稱（例如：日結_成交明細）：",
        )
        if not ok or not name.strip():
            return
        rules = self._parse_filter()
        try:
            path = filter_presets.save_preset(name.strip(), rules)
        except ValueError as exc:
            QMessageBox.warning(self, "儲存失敗", str(exc))
            return
        QMessageBox.information(self, "已儲存", f"已儲存至：\n{path}")
        self._filter_preset_combo.clear()
        self._filter_preset_combo.addItem("（選擇 preset）", "")
        for preset_name in filter_presets.list_presets():
            self._filter_preset_combo.addItem(preset_name, preset_name)
        idx = self._filter_preset_combo.findData(name.strip())
        if idx >= 0:
            self._filter_preset_combo.setCurrentIndex(idx)

    def _refresh_preview(self) -> None:
        from app.services.folder_import import scan_folder

        folder = self.folder_path()
        if folder is None or not folder.is_dir():
            QMessageBox.warning(self, "預覽", "請先選擇有效的資料夾。")
            return
        rules = self._parse_filter()
        try:
            self._last_scan = scan_folder(
                folder,
                recursive=self._recursive.isChecked(),
                name_filter=rules,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "預覽失敗", str(exc))
            return

        self._preview_list.clear()
        for path in self._last_scan.matched:
            QListWidgetItem(f"✓ {path.name}", self._preview_list)
        for path in self._last_scan.skipped:
            QListWidgetItem(f"－ {path.name}（略過）", self._preview_list)

        n_match = len(self._last_scan.matched)
        n_skip = len(self._last_scan.skipped)
        self._preview_label.setText(
            f"符合 {n_match} 個，略過 {n_skip} 個｜{rules.summary()}"
        )

    def _on_accept(self) -> None:
        if self._last_scan is None:
            self._refresh_preview()
        if self._last_scan is None or not self._last_scan.matched:
            QMessageBox.warning(
                self,
                "無符合檔案",
                "沒有符合關鍵字條件的 Excel。\n請調整關鍵字或按「預覽符合檔案」確認。",
            )
            return
        self._filter = self._parse_filter()
        self.accept()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇資料夾", self._path_edit.text())
        if path:
            self._path_edit.setText(path)
            self._last_scan = None
            self._preview_label.setText("資料夾已變更，請按「預覽符合檔案」")

    def folder_path(self) -> Path | None:
        text = self._path_edit.text().strip()
        return Path(text) if text else None

    def recursive(self) -> bool:
        return self._recursive.isChecked()

    def watch_enabled(self) -> bool:
        return self._enable_watch.isChecked()

    def name_filter(self):
        return self._filter

    def matched_paths(self) -> list[Path]:
        if self._last_scan is None:
            return []
        return list(self._last_scan.matched)
