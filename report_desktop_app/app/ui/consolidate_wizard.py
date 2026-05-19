"""Multi-step wizard: select ranges → merge many Excel files into one."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from app.core import config
from app.core.range_spec import SourceRangeSpec
from app.core.schemas import LoadedFile
from app.services.consolidation_service import ConsolidateRequest, MergeMode
from app.ui.dialogs import RangeSelectionDialog


class ConsolidateWizard(QWizard):
    """Three-step flow: files → ranges → output options."""

    def __init__(
        self,
        files: list[LoadedFile],
        *,
        default_output_dir: Path,
        default_template: Path | None = None,
        initial_merge_mode: MergeMode | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("合併多檔 Excel")
        self.resize(620, 480)
        self._files = list(files)
        self._ranges: dict[Path, SourceRangeSpec] = {
            f.path: f.source_range for f in self._files
        }

        self._page_files = _FilesPage(self._files)
        self._page_ranges = _RangesPage(self._files, self._ranges)
        self._page_output = _OutputPage(
            default_output_dir,
            default_template,
            initial_merge_mode=initial_merge_mode,
        )

        self.addPage(self._page_files)
        self.addPage(self._page_ranges)
        self.addPage(self._page_output)

    def build_request(self) -> ConsolidateRequest:
        sources = [(f.path, self._ranges[f.path]) for f in self._files]
        return self._page_output.to_request(sources)


class _FilesPage(QWizardPage):
    def __init__(self, files: list[LoadedFile]) -> None:
        super().__init__()
        self.setTitle("步驟 1：確認來源檔案")
        self.setSubTitle("將依序讀取下列檔案中您指定的範圍，合併到一個 Excel。")

        layout = QVBoxLayout(self)
        lines = [f"• {f.path.name}（{f.row_count:,} 列預估）" for f in files]
        layout.addWidget(QLabel("\n".join(lines) if lines else "（無檔案）"))


class _RangesPage(QWizardPage):
    def __init__(
        self,
        files: list[LoadedFile],
        ranges: dict[Path, SourceRangeSpec],
    ) -> None:
        super().__init__()
        self.setTitle("步驟 2：選擇每個檔案的資料範圍")
        self.setSubTitle(
            "下列每一個 Excel 可各自設定複製區域。"
            "點選一列後按「設定範圍…」，或連按兩下該檔案。"
        )

        self._files = files
        self._ranges = ranges

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("每個檔案獨立範圍（例如 4 個來源檔請逐檔設定，互不干擾）：")
        )

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _: self._edit_range())
        self._refresh_list()
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("設定範圍…")
        edit_btn.clicked.connect(self._edit_range)
        apply_all_btn = QPushButton("將選取檔的範圍套用到全部")
        apply_all_btn.clicked.connect(self._apply_to_all)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(apply_all_btn)
        layout.addLayout(btn_row)

    def _refresh_list(self) -> None:
        current_path: Path | None = None
        item = self._list.currentItem()
        if item is not None:
            current_path = item.data(Qt.ItemDataRole.UserRole)

        self._list.clear()
        for loaded in self._files:
            spec = self._ranges[loaded.path]
            text = f"{loaded.path.name}\n    → {spec.summary()}"
            row = QListWidgetItem(text)
            row.setData(Qt.ItemDataRole.UserRole, loaded.path)
            self._list.addItem(row)
            if current_path == loaded.path:
                self._list.setCurrentItem(row)

        if self._list.currentRow() < 0 and self._list.count():
            self._list.setCurrentRow(0)

    def _current_path(self) -> Path | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _loaded_for_path(self, path: Path) -> LoadedFile | None:
        for loaded in self._files:
            if loaded.path == path:
                return loaded
        return None

    def _edit_range(self) -> None:
        path = self._current_path()
        loaded = self._loaded_for_path(path) if path else None
        if not loaded:
            return
        dialog = RangeSelectionDialog(
            path=loaded.path,
            sheet_names=loaded.sheet_names,
            current=self._ranges[loaded.path],
            parent=self,
        )
        if dialog.exec():
            self._ranges[loaded.path] = dialog.range_spec()
            self._refresh_list()

    def _apply_to_all(self) -> None:
        path = self._current_path()
        if path is None:
            return
        spec = self._ranges[path]
        for item in self._files:
            self._ranges[item.path] = SourceRangeSpec(
                sheet=spec.sheet,
                header_row=spec.header_row,
                start_row=spec.start_row,
                end_row=spec.end_row,
                start_column=spec.start_column,
                end_column=spec.end_column,
                excel_range=spec.excel_range,
            )
        self._refresh_list()


class _OutputPage(QWizardPage):
    def __init__(
        self,
        output_dir: Path,
        template: Path | None,
        *,
        initial_merge_mode: MergeMode | None = None,
    ) -> None:
        super().__init__()
        self.setTitle("步驟 3：輸出選項")
        self.setSubTitle("可合併到單一工作表，或每個來源一個工作表；可選用範本建立新檔。")

        self._output_dir = Path(output_dir)
        self._template = template

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._filename = QLineEdit("merged_sources.xlsx")
        form.addRow("檔案名稱：", self._filename)

        out_row = QHBoxLayout()
        self._out_edit = QLineEdit(str(self._output_dir))
        browse = QPushButton("瀏覽…")
        browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_edit)
        out_row.addWidget(browse)
        form.addRow("輸出資料夾：", out_row)

        layout.addLayout(form)

        self._single = QRadioButton("合併到單一工作表（加 _source_file 欄）")
        self._per_file = QRadioButton("每個來源一個工作表")
        if initial_merge_mode == "one_sheet_per_file":
            self._per_file.setChecked(True)
        else:
            self._single.setChecked(True)
        layout.addWidget(self._single)
        layout.addWidget(self._per_file)

        self._use_template = QCheckBox("使用範本建立新檔案（在範本基礎上寫入資料）")
        layout.addWidget(self._use_template)

        tpl_row = QHBoxLayout()
        self._tpl_edit = QLineEdit(str(template or config.TEMPLATE_FILES["daily"]))
        tpl_browse = QPushButton("瀏覽…")
        tpl_browse.clicked.connect(self._browse_template)
        tpl_row.addWidget(self._tpl_edit)
        tpl_row.addWidget(tpl_browse)
        layout.addLayout(tpl_row)
        self._use_template.toggled.connect(self._tpl_edit.setEnabled)
        self._use_template.toggled.connect(tpl_browse.setEnabled)
        self._tpl_edit.setEnabled(False)
        tpl_browse.setEnabled(False)

        self._import_after = QCheckBox("合併完成後自動匯入合併檔（加入左側檔案清單）")
        self._import_after.setChecked(True)
        layout.addWidget(self._import_after)

        self._open_mapping = QCheckBox("匯入後開啟欄位映射（接續產報）")
        layout.addWidget(self._open_mapping)
        self._import_after.toggled.connect(self._open_mapping.setEnabled)
        self._open_mapping.setEnabled(True)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "輸出資料夾", self._out_edit.text())
        if path:
            self._out_edit.setText(path)

    def _browse_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇範本",
            self._tpl_edit.text(),
            "Excel (*.xlsx)",
        )
        if path:
            self._tpl_edit.setText(path)

    def to_request(self, sources: list[tuple[Path, SourceRangeSpec]]) -> ConsolidateRequest:
        merge_mode: MergeMode = (
            "one_sheet_per_file" if self._per_file.isChecked() else "single_sheet"
        )
        out_path = Path(self._out_edit.text()) / self._filename.text().strip()
        return ConsolidateRequest(
            sources=sources,
            output_path=out_path,
            merge_mode=merge_mode,
            use_template=self._use_template.isChecked(),
            template_path=Path(self._tpl_edit.text()) if self._use_template.isChecked() else None,
            import_after_merge=self._import_after.isChecked(),
            open_mapping_after_merge=self._open_mapping.isChecked(),
        )
