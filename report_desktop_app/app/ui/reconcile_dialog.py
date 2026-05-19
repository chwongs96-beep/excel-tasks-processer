"""Dialog to reconcile two Excel sources (e.g. broker vs GL)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.core.schemas import LoadedFile
from app.services.reconcile_service import ReconcileRequest


class ReconcileDialog(QDialog):
    """Pick two imported files, key columns, and optional amount check."""

    def __init__(
        self,
        files: list[LoadedFile],
        *,
        default_output_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("資料對帳")
        self.resize(520, 420)
        self._files = files
        self._default_output_dir = default_output_dir
        self._result_path: Path | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "比對兩份 Excel（例如券商明細 vs 系統匯出）。"
                "請先確認兩邊已設定正確的讀取範圍。"
            )
        )

        form = QFormLayout()
        self._left = QComboBox()
        self._right = QComboBox()
        for loaded in files:
            label = loaded.path.name
            self._left.addItem(label, loaded)
            self._right.addItem(label, loaded)
        if self._left.count() > 1:
            self._right.setCurrentIndex(1)
        form.addRow("左側（基準）檔：", self._left)
        form.addRow("右側（比對）檔：", self._right)
        layout.addLayout(form)

        keys_group = QGroupBox("對帳鍵（可多選，建議：日期 + 帳號 + 金額）")
        keys_layout = QVBoxLayout(keys_group)
        self._key_checks: list[tuple[str, QCheckBox]] = []
        self._keys_container = QVBoxLayout()
        keys_layout.addLayout(self._keys_container)
        layout.addWidget(keys_group)

        amount_row = QHBoxLayout()
        self._amount = QComboBox()
        self._amount.addItem("（不比對金額）", "")
        amount_row.addWidget(self._amount, stretch=1)
        layout.addWidget(QLabel("金額欄（選填）："))
        layout.addLayout(amount_row)

        tol_row = QHBoxLayout()
        self._tolerance = QDoubleSpinBox()
        self._tolerance.setDecimals(4)
        self._tolerance.setRange(0, 1_000_000)
        self._tolerance.setValue(0.01)
        tol_row.addWidget(QLabel("金額容許差："))
        tol_row.addWidget(self._tolerance)
        layout.addLayout(tol_row)

        self._export = QCheckBox("完成後匯出對帳結果 Excel")
        self._export.setChecked(True)
        layout.addWidget(self._export)

        out_row = QHBoxLayout()
        self._out_name = QLineEdit("reconcile_diff.xlsx")
        out_row.addWidget(self._out_name)
        layout.addWidget(QLabel("匯出檔名："))
        layout.addLayout(out_row)

        self._left.currentIndexChanged.connect(self._refresh_columns)
        self._right.currentIndexChanged.connect(self._refresh_columns)
        self._refresh_columns()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        run_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if run_btn:
            run_btn.setText("執行對帳")
        buttons.accepted.connect(self._validate_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _shared_columns(self) -> list[str]:
        left: LoadedFile = self._left.currentData()
        right: LoadedFile = self._right.currentData()
        if not left or not right:
            return []
        return sorted(set(left.columns) & set(right.columns))

    def _refresh_columns(self) -> None:
        while self._keys_container.count():
            item = self._keys_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._key_checks.clear()

        columns = self._shared_columns()
        schema = __import__("app.core.config", fromlist=["config"]).config.load_schema_config()
        preferred = [f.name for f in schema.fields if f.name in columns]

        for col in columns:
            box = QCheckBox(col)
            if col in preferred:
                box.setChecked(True)
            self._keys_container.addWidget(box)
            self._key_checks.append((col, box))

        self._amount.clear()
        self._amount.addItem("（不比對金額）", "")
        for col in columns:
            if col in ("amount", "debit", "credit", "金額", "借方", "貸方") or "amount" in col.lower():
                self._amount.addItem(col, col)
        for col in columns:
            self._amount.addItem(col, col)

    def _validate_accept(self) -> None:
        if self._left.currentData() == self._right.currentData():
            QMessageBox.warning(self, "對帳", "請選擇兩個不同的檔案。")
            return
        if not self.selected_key_columns():
            QMessageBox.warning(self, "對帳", "請至少勾選一個對帳鍵欄位。")
            return
        self.accept()

    def selected_key_columns(self) -> list[str]:
        return [name for name, box in self._key_checks if box.isChecked()]

    def build_request(self) -> ReconcileRequest:
        left: LoadedFile = self._left.currentData()
        right: LoadedFile = self._right.currentData()
        amount = self._amount.currentData() or None
        output_path = None
        if self._export.isChecked():
            output_path = self._default_output_dir / self._out_name.text().strip()
        return ReconcileRequest(
            left_path=left.path,
            right_path=right.path,
            left_range=left.source_range,
            right_range=right.source_range,
            key_columns=self.selected_key_columns(),
            amount_column=str(amount) if amount else None,
            tolerance=self._tolerance.value(),
            output_path=output_path,
        )
