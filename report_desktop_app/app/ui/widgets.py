"""Reusable Qt widgets for the reporting desktop UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core import config
from app.core.schemas import DateSpec, ReportType
from app.ui.help_text import BUTTON_TOOLTIPS
from app.ui.styles import current_theme
from app.ui.table_model import DataFrameTableModel
from app.ui.ui_metrics import (
    BTN_HEIGHT,
    BTN_HEIGHT_COMPACT,
    BTN_HEIGHT_PRIMARY,
    FILE_LIST_MIN_H,
    FILE_LIST_PREF_H,
    LOG_MIN_H,
    LOG_PREF_H,
    PREVIEW_MIN_H,
    SIDEBAR_MAX_W,
    SIDEBAR_MIN_W,
    TABLE_ROW_HEIGHT,
)
from app.ui.ui_utils import (
    card_frame,
    hint_label,
    mark_primary,
    mark_secondary,
    mark_tool,
    set_tooltip,
    sized_button,
)


class StatusLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("status", "info")
        self.setText("就緒")

    def show_info(self, text: str) -> None:
        self.setProperty("status", "info")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(text)

    def show_error(self, text: str) -> None:
        self.setProperty("status", "error")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(text)

    def show_success(self, text: str) -> None:
        self.setProperty("status", "success")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(text)


class FileImportPanel(QWidget):
    add_clicked = Signal()
    add_folder_clicked = Signal()
    adjustment_clicked = Signal()
    remove_clicked = Signal()
    clear_clicked = Signal()
    mapping_clicked = Signal()
    range_clicked = Signal()
    consolidate_clicked = Signal()
    reconcile_clicked = Signal()
    clear_range_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        frame, layout = card_frame()

        self._list = QListWidget()
        self._list.setObjectName("fileList")
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setUniformItemSizes(True)
        self._list.setWordWrap(False)
        self._list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.setMinimumHeight(FILE_LIST_MIN_H)
        self._list.setMaximumHeight(FILE_LIST_PREF_H)
        self._list.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._list.itemDoubleClicked.connect(self.range_clicked.emit)
        layout.addWidget(self._list)

        quick_select = QHBoxLayout()
        quick_select.setSpacing(8)
        self._select_all_btn = sized_button("全選", height=BTN_HEIGHT_COMPACT)
        self._invert_btn = sized_button("反選", height=BTN_HEIGHT_COMPACT)
        self._keyword_select_btn = sized_button("關鍵字選取…", height=BTN_HEIGHT_COMPACT)
        for btn in (self._select_all_btn, self._invert_btn, self._keyword_select_btn):
            mark_tool(btn)
            quick_select.addWidget(btn)
        quick_select.addStretch()
        self._select_all_btn.clicked.connect(self._select_all)
        self._invert_btn.clicked.connect(self._invert_selection)
        self._keyword_select_btn.clicked.connect(self._select_by_keyword)
        layout.addLayout(quick_select)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self._add_btn = sized_button("＋ 新增檔案", height=BTN_HEIGHT)
        self._folder_btn = sized_button("資料夾", height=BTN_HEIGHT, min_width=88)
        mark_secondary(self._add_btn)
        mark_secondary(self._folder_btn)
        self._add_btn.clicked.connect(self.add_clicked.emit)
        self._folder_btn.clicked.connect(self.add_folder_clicked.emit)
        row1.addWidget(self._add_btn, stretch=1)
        row1.addWidget(self._folder_btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self._map_btn = sized_button("欄位映射", height=BTN_HEIGHT)
        self._range_btn = sized_button("設定範圍", height=BTN_HEIGHT)
        mark_primary(self._map_btn)
        mark_secondary(self._range_btn)
        self._map_btn.clicked.connect(self.mapping_clicked.emit)
        self._range_btn.clicked.connect(self.range_clicked.emit)
        row2.addWidget(self._map_btn, stretch=1)
        row2.addWidget(self._range_btn, stretch=1)
        layout.addLayout(row2)

        tools = QGridLayout()
        tools.setHorizontalSpacing(8)
        tools.setVerticalSpacing(8)
        compact_h = BTN_HEIGHT_COMPACT
        self._merge_btn = sized_button("合併", height=compact_h)
        self._reconcile_btn = sized_button("對帳", height=compact_h)
        self._adj_btn = sized_button("調整", height=compact_h)
        self._remove_btn = sized_button("移除", height=compact_h)
        self._clear_range_btn = sized_button("清範圍", height=compact_h)
        self._clear_btn = sized_button("全清", height=compact_h)
        for btn in (
            self._merge_btn,
            self._reconcile_btn,
            self._adj_btn,
            self._remove_btn,
            self._clear_range_btn,
            self._clear_btn,
        ):
            mark_tool(btn)
        self._merge_btn.clicked.connect(self.consolidate_clicked.emit)
        self._reconcile_btn.clicked.connect(self.reconcile_clicked.emit)
        self._adj_btn.clicked.connect(self.adjustment_clicked.emit)
        self._remove_btn.clicked.connect(self.remove_clicked.emit)
        self._clear_range_btn.clicked.connect(self.clear_range_clicked.emit)
        self._clear_btn.clicked.connect(self.clear_clicked.emit)
        tools.addWidget(self._merge_btn, 0, 0)
        tools.addWidget(self._reconcile_btn, 0, 1)
        tools.addWidget(self._adj_btn, 1, 0)
        tools.addWidget(self._remove_btn, 1, 1)
        tools.addWidget(self._clear_range_btn, 2, 0)
        tools.addWidget(self._clear_btn, 2, 1)
        layout.addLayout(tools)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        set_tooltip(self._add_btn, BUTTON_TOOLTIPS["add"])
        set_tooltip(self._folder_btn, BUTTON_TOOLTIPS["folder"])
        set_tooltip(self._map_btn, BUTTON_TOOLTIPS["mapping"])
        set_tooltip(self._range_btn, BUTTON_TOOLTIPS["range"])
        set_tooltip(self._merge_btn, BUTTON_TOOLTIPS["merge"])
        set_tooltip(self._reconcile_btn, BUTTON_TOOLTIPS["reconcile"])
        set_tooltip(self._adj_btn, BUTTON_TOOLTIPS["adjustment"])
        set_tooltip(self._clear_range_btn, BUTTON_TOOLTIPS["clear_range"])
        set_tooltip(self._select_all_btn, "選取目前清單中的所有檔案。")
        set_tooltip(self._invert_btn, "將目前選取反轉（已選改未選，未選改已選）。")
        set_tooltip(self._keyword_select_btn, "輸入關鍵字後，快速選取檔名符合的項目。")

    def set_import_enabled(self, enabled: bool) -> None:
        for btn in (
            self._add_btn,
            self._folder_btn,
            self._adj_btn,
            self._remove_btn,
            self._map_btn,
            self._range_btn,
            self._merge_btn,
            self._reconcile_btn,
            self._clear_range_btn,
            self._clear_btn,
            self._select_all_btn,
            self._invert_btn,
            self._keyword_select_btn,
        ):
            btn.setEnabled(enabled)

    def set_files(self, items: list[tuple[str, int, str, str, str]]) -> None:
        self._list.clear()
        if not items:
            placeholder = QListWidgetItem("（尚未匯入檔案，請按「新增檔案」或拖曳 Excel）", self._list)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return
        for name, rows, range_hint, status, full_path in items:
            text = f"{name}  ｜  {rows:,} 列  ·  {range_hint}  ·  {status}"
            item = QListWidgetItem(text, self._list)
            item.setToolTip(f"{text}\n{full_path}")

    def selected_index(self) -> int:
        row = self._list.currentRow()
        return row if row >= 0 else -1

    def selected_indices(self) -> list[int]:
        rows = sorted({item.row() for item in self._list.selectedIndexes()})
        return [row for row in rows if row >= 0]

    def _select_all(self) -> None:
        self._list.selectAll()

    def _invert_selection(self) -> None:
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item is None:
                continue
            item.setSelected(not item.isSelected())

    def _select_by_keyword(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(self, "關鍵字選取", "輸入檔名關鍵字（可用逗號分隔）：")
        if not ok:
            return
        keyword_raw = text.strip()
        if not keyword_raw:
            return
        keywords = [part.strip().lower() for part in keyword_raw.replace(";", ",").split(",")]
        keywords = [item for item in keywords if item]
        if not keywords:
            return
        matched = 0
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item is None:
                continue
            name = item.text().splitlines()[0].lower()
            hit = any(keyword in name for keyword in keywords)
            item.setSelected(hit)
            if hit:
                matched += 1
        if matched == 0:
            QMessageBox.information(self, "關鍵字選取", "沒有符合關鍵字的檔案。")

    def select_index(self, index: int) -> None:
        if 0 <= index < self._list.count():
            self._list.setCurrentRow(index)


class ReportTypeSelector(QGroupBox):
    report_type_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("報表類型", parent)
        self._daily = QRadioButton("日報")
        self._weekly = QRadioButton("週報")
        self._monthly = QRadioButton("月報")
        self._daily.setChecked(True)

        group = QButtonGroup(self)
        group.addButton(self._daily, 0)
        group.addButton(self._weekly, 1)
        group.addButton(self._monthly, 2)
        group.idClicked.connect(self._on_id_clicked)

        row = QHBoxLayout(self)
        row.addWidget(self._daily)
        row.addWidget(self._weekly)
        row.addWidget(self._monthly)
        row.addStretch()

    def _on_id_clicked(self, button_id: int) -> None:
        mapping = {0: "daily", 1: "weekly", 2: "monthly"}
        self.report_type_changed.emit(mapping[button_id])

    def report_type(self) -> ReportType:
        if self._weekly.isChecked():
            return "weekly"
        if self._monthly.isChecked():
            return "monthly"
        return "daily"

    def set_report_type(self, report_type: ReportType) -> None:
        if report_type == "weekly":
            self._weekly.setChecked(True)
        elif report_type == "monthly":
            self._monthly.setChecked(True)
        else:
            self._daily.setChecked(True)


class DateRangeSelector(QGroupBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("期間", parent)
        self._stack = QStackedWidget()

        daily_page = QWidget()
        daily_form = QFormLayout(daily_page)
        daily_form.setContentsMargins(0, 0, 0, 0)
        self._daily_date = QDateEdit(calendarPopup=True)
        self._daily_date.setDisplayFormat("yyyy-MM-dd")
        self._daily_date.setDate(QDate.currentDate())
        daily_form.addRow("日期", self._daily_date)
        self._stack.addWidget(daily_page)

        weekly_page = QWidget()
        weekly_form = QFormLayout(weekly_page)
        weekly_form.setContentsMargins(0, 0, 0, 0)
        self._week_start = QDateEdit(calendarPopup=True)
        self._week_end = QDateEdit(calendarPopup=True)
        for widget in (self._week_start, self._week_end):
            widget.setDisplayFormat("yyyy-MM-dd")
        self._week_start.setDate(QDate.currentDate().addDays(-(QDate.currentDate().dayOfWeek() - 1)))
        self._week_end.setDate(QDate.currentDate())
        weekly_form.addRow("起始", self._week_start)
        weekly_form.addRow("結束", self._week_end)
        self._stack.addWidget(weekly_page)

        monthly_page = QWidget()
        monthly_form = QFormLayout(monthly_page)
        monthly_form.setContentsMargins(0, 0, 0, 0)
        self._month_date = QDateEdit(calendarPopup=True)
        self._month_date.setDisplayFormat("yyyy-MM")
        self._month_date.setDate(QDate.currentDate())
        monthly_form.addRow("月份", self._month_date)
        self._stack.addWidget(monthly_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(self._stack)

    def set_report_type(self, report_type: ReportType) -> None:
        index = {"daily": 0, "weekly": 1, "monthly": 2}[report_type]
        self._stack.setCurrentIndex(index)

    @staticmethod
    def _qdate_to_date(qdate: QDate) -> date:
        return date(qdate.year(), qdate.month(), qdate.day())

    def build_date_spec(self, report_type: ReportType) -> DateSpec:
        if report_type == "daily":
            return DateSpec(
                report_type="daily",
                trade_date=self._qdate_to_date(self._daily_date.date()),
            )
        if report_type == "weekly":
            return DateSpec(
                report_type="weekly",
                week_start=self._qdate_to_date(self._week_start.date()),
                week_end=self._qdate_to_date(self._week_end.date()),
            )
        month_q = self._month_date.date()
        return DateSpec(
            report_type="monthly",
            month=date(month_q.year(), month_q.month(), 1),
        )


class TemplateSelector(QWidget):
    template_changed = Signal(str)
    browse_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._emit_path)
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(36)
        mark_secondary(browse_btn)
        browse_btn.clicked.connect(self.browse_clicked.emit)
        row = QHBoxLayout()
        row.addWidget(self._combo, stretch=1)
        row.addWidget(browse_btn)
        wrap = QWidget()
        wrap.setLayout(row)
        form.addRow("範本", wrap)
        self.reload_templates()

    def reload_templates(self) -> None:
        self._combo.blockSignals(True)
        self._combo.clear()
        for key, path in config.TEMPLATE_FILES.items():
            self._combo.addItem(f"{key} · {path.name}", str(path))
        self._combo.blockSignals(False)

    def _emit_path(self) -> None:
        path = self.template_path()
        if path:
            self.template_changed.emit(path)

    def template_path(self) -> str:
        return self._combo.currentData() or ""

    def set_template_path(self, path: str | Path) -> None:
        path_str = str(path)
        index = self._combo.findData(path_str)
        if index >= 0:
            self._combo.setCurrentIndex(index)
        else:
            self._combo.addItem(Path(path_str).name, path_str)
            self._combo.setCurrentIndex(self._combo.count() - 1)

    def sync_to_report_type(self, report_type: ReportType) -> None:
        path = config.TEMPLATE_FILES.get(report_type)
        if path:
            self.set_template_path(path)


class OutputPathSelector(QWidget):
    path_changed = Signal(str)
    browse_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self._path_edit = QLineEdit(str(config.OUTPUT_DIR))
        self._path_edit.setReadOnly(True)
        self._path_edit.setMinimumWidth(180)
        browse_btn = sized_button("…", height=BTN_HEIGHT - 2, min_width=44)
        mark_secondary(browse_btn)
        browse_btn.clicked.connect(self.browse_clicked.emit)
        row = QHBoxLayout()
        row.addWidget(self._path_edit, stretch=1)
        row.addWidget(browse_btn)
        wrap = QWidget()
        wrap.setLayout(row)
        form.addRow("輸出", wrap)

    def output_path(self) -> str:
        return self._path_edit.text().strip()

    def set_output_path(self, path: str | Path) -> None:
        self._path_edit.setText(str(path))
        self.path_changed.emit(str(path))


class ReportOptionsPanel(QWidget):
    """Report type, period, template, output in one card."""

    report_type_changed = Signal(str)
    template_changed = Signal(str)
    output_path_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        frame, layout = card_frame()

        self.report_type = ReportTypeSelector()
        self.date_range = DateRangeSelector()
        self.template = TemplateSelector()
        self.output = OutputPathSelector()

        layout.addWidget(self.report_type)
        layout.addWidget(self.date_range)
        layout.addWidget(self.template)
        layout.addWidget(self.output)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        self.report_type.report_type_changed.connect(self._on_report_type)
        self.template.template_changed.connect(self.template_changed.emit)
        self.output.path_changed.connect(self.output_path_changed.emit)

    def _on_report_type(self, report_type: str) -> None:
        self.date_range.set_report_type(report_type)  # type: ignore[arg-type]
        self.template.sync_to_report_type(report_type)  # type: ignore[arg-type]
        self.report_type_changed.emit(report_type)


class ActionButtonPanel(QWidget):
    validate_clicked = Signal()
    preview_clicked = Signal()
    generate_clicked = Signal()
    open_folder_clicked = Signal()
    audit_log_clicked = Signal()
    batch_generate_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        frame, layout = card_frame("產出")

        row = QHBoxLayout()
        row.setSpacing(10)
        self._validate_btn = sized_button("驗證資料", height=BTN_HEIGHT)
        self._preview_btn = sized_button("預覽轉換", height=BTN_HEIGHT)
        mark_secondary(self._validate_btn)
        mark_secondary(self._preview_btn)
        self._validate_btn.clicked.connect(self.validate_clicked.emit)
        self._preview_btn.clicked.connect(self.preview_clicked.emit)
        row.addWidget(self._validate_btn, stretch=1)
        row.addWidget(self._preview_btn, stretch=1)
        layout.addLayout(row)

        self._generate_btn = sized_button("產生報表", height=BTN_HEIGHT_PRIMARY)
        mark_primary(self._generate_btn)
        self._generate_btn.setDefault(True)
        self._generate_btn.clicked.connect(self.generate_clicked.emit)
        layout.addWidget(self._generate_btn)

        extras = QHBoxLayout()
        extras.setSpacing(8)
        self._batch_btn = sized_button("批次日報", height=BTN_HEIGHT - 4)
        self._open_btn = sized_button("輸出夾", height=BTN_HEIGHT - 4)
        self._audit_btn = sized_button("紀錄", height=BTN_HEIGHT - 4)
        for btn in (self._batch_btn, self._open_btn, self._audit_btn):
            mark_secondary(btn)
        self._batch_btn.clicked.connect(self.batch_generate_clicked.emit)
        self._open_btn.clicked.connect(self.open_folder_clicked.emit)
        self._audit_btn.clicked.connect(self.audit_log_clicked.emit)
        extras.addWidget(self._batch_btn)
        extras.addWidget(self._open_btn)
        extras.addWidget(self._audit_btn)
        layout.addLayout(extras)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        set_tooltip(self._validate_btn, BUTTON_TOOLTIPS["validate"])
        set_tooltip(self._preview_btn, BUTTON_TOOLTIPS["preview"])
        set_tooltip(self._generate_btn, BUTTON_TOOLTIPS["generate"])
        set_tooltip(self._batch_btn, BUTTON_TOOLTIPS["batch"])

    def set_actions_enabled(self, enabled: bool) -> None:
        self._validate_btn.setEnabled(enabled)
        self._preview_btn.setEnabled(enabled)
        self._generate_btn.setEnabled(enabled)
        self._batch_btn.setEnabled(enabled)


class LogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = QTextEdit()
        self._text.setObjectName("logPanel")
        self._text.setAcceptRichText(True)
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("操作訊息…")
        self._text.setMinimumHeight(LOG_MIN_H)
        self._text.setMaximumHeight(LOG_PREF_H)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    def append(self, message: str, *, level: str = "info") -> None:
        theme = current_theme()
        colors = {
            "info": theme.status_info,
            "warning": theme.status_warning,
            "error": theme.status_error,
            "success": theme.status_success,
        }
        prefix = {"info": "ℹ", "warning": "⚠", "error": "✕", "success": "✓"}.get(level, "·")
        color = colors.get(level, colors["info"])
        self._text.append(f'<span style="color:{color}">{prefix}</span> {message}')
        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().maximum())

    def clear(self) -> None:
        self._text.clear()


class DataPreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        card = QFrame()
        card.setObjectName("previewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card.setMinimumHeight(PREVIEW_MIN_H)

        self._caption = QLabel("資料預覽")
        self._caption.setObjectName("previewTitle")
        self._meta = QLabel("匯入檔案後可在此檢視原始與轉換結果")
        self._meta.setProperty("role", "hint")

        self._tabs = QTabWidget()
        self._raw_view = self._make_table_view()
        self._transformed_view = self._make_table_view()
        self._reconcile_view = self._make_table_view()
        self._tabs.addTab(self._wrap_view(self._raw_view), "原始")
        self._tabs.addTab(self._wrap_view(self._transformed_view), "轉換後")
        self._tabs.addTab(self._wrap_view(self._reconcile_view), "對帳差異")

        card_layout.addWidget(self._caption)
        card_layout.addWidget(self._meta)
        card_layout.addWidget(self._tabs, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)

    @staticmethod
    def _make_table_view() -> QTableView:
        view = QTableView()
        view.setAlternatingRowColors(True)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.horizontalHeader().setStretchLastSection(True)
        view.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        return view

    @staticmethod
    def _wrap_view(view: QTableView) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(view)
        return container

    def bind_models(
        self,
        raw_model: DataFrameTableModel,
        transformed_model: DataFrameTableModel,
        reconcile_model: DataFrameTableModel | None = None,
    ) -> None:
        self._raw_view.setModel(raw_model)
        self._transformed_view.setModel(transformed_model)
        if reconcile_model is not None:
            self._reconcile_view.setModel(reconcile_model)

    def set_caption(self, text: str) -> None:
        self._caption.setText(text)

    def set_reconcile_summary(self, text: str) -> None:
        self._meta.setText(text)
        self._meta.show()

    def show_raw_tab(self) -> None:
        self._tabs.setCurrentIndex(0)

    def show_transformed_tab(self) -> None:
        self._tabs.setCurrentIndex(1)

    def show_reconcile_tab(self) -> None:
        self._tabs.setCurrentIndex(2)


class ReportSettingsPanel(QWidget):
    report_type_changed = Signal(str)
    template_changed = Signal(str)
    output_path_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(SIDEBAR_MIN_W)
        self.setMaximumWidth(SIDEBAR_MAX_W)

        self.files = FileImportPanel()
        self.report_options = ReportOptionsPanel()
        self.actions = ActionButtonPanel()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebarHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 8)
        header_layout.setSpacing(4)

        title = QLabel("證券會計報表")
        title.setObjectName("sidebarTitle")
        sub = QLabel("Excel 匯入 · 映射 · 產報")
        sub.setObjectName("sidebarSubtitle")
        scroll_hint = QLabel("↓ 中間區塊可捲動；產出按鈕固定於下方")
        scroll_hint.setObjectName("sidebarScrollHint")
        scroll_hint.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        header_layout.addWidget(scroll_hint)
        root.addWidget(header)

        scroll_body = QWidget()
        scroll_body.setObjectName("sidebarContent")
        scroll_body.setMinimumWidth(SIDEBAR_MIN_W - 24)
        body_layout = QVBoxLayout(scroll_body)
        body_layout.setContentsMargins(12, 4, 12, 12)
        body_layout.setSpacing(12)

        sec1 = QLabel("① 資料來源")
        sec1.setObjectName("sidebarSection")
        sec2 = QLabel("② 報表設定")
        sec2.setObjectName("sidebarSection")
        body_layout.addWidget(sec1)
        body_layout.addWidget(self.files)
        body_layout.addWidget(sec2)
        body_layout.addWidget(self.report_options)

        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(scroll_body)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        root.addWidget(scroll, stretch=1)

        footer = QWidget()
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 12)
        footer_layout.setSpacing(0)
        footer_layout.addWidget(self.actions)
        root.addWidget(footer)

        self.report_options.report_type_changed.connect(self.report_type_changed.emit)
        self.report_options.template_changed.connect(self.template_changed.emit)
        self.report_options.output.path_changed.connect(self.output_path_changed.emit)

    @property
    def report_type(self) -> ReportTypeSelector:
        return self.report_options.report_type

    @property
    def date_range(self) -> DateRangeSelector:
        return self.report_options.date_range

    @property
    def template(self) -> TemplateSelector:
        return self.report_options.template

    @property
    def output(self) -> OutputPathSelector:
        return self.report_options.output
