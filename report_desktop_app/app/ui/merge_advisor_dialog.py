"""Ask the user their goal and recommend the smartest merge approach."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)

from app.services.merge_advisor import MergeAdvice, MergeModeChoice, advise_merge


class MergeAdvisorDialog(QDialog):
    """Step 0 before consolidate wizard — recommends mode with explanation."""

    def __init__(self, file_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("智慧合併建議")
        self.resize(560, 480)
        self._file_count = max(1, file_count)
        self._advice: MergeAdvice | None = None
        self._chosen_mode: MergeModeChoice = "single_sheet"

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                f"已選擇 <b>{file_count}</b> 個 Excel。"
                "請回答下列問題，系統會建議最適合的做法（可再於精靈中調整）。"
            )
        )

        goal_box = QGroupBox("1. 您的主要目標？")
        goal_layout = QVBoxLayout(goal_box)
        self._goal_group = QButtonGroup(self)
        self._goal_stack = QRadioButton("把多檔的「資料列」接成一份總明細（會計最常用）")
        self._goal_sheets = QRadioButton("每個檔案保留成獨立工作表（分檔對照）")
        self._goal_tabs = QRadioButton("只搬移 Excel 分頁，保留公式與完整格式")
        self._goal_stack.setChecked(True)
        for i, btn in enumerate((self._goal_stack, self._goal_sheets, self._goal_tabs)):
            self._goal_group.addButton(btn, i)
            goal_layout.addWidget(btn)
        layout.addWidget(goal_box)

        opt_box = QGroupBox("2. 其他條件")
        opt_layout = QVBoxLayout(opt_box)
        self._same_headers = QCheckBox("各檔第一列欄位名稱大致相同")
        self._same_headers.setChecked(True)
        self._need_formulas = QCheckBox("必須保留來源檔內的公式／合併儲存格原樣")
        opt_layout.addWidget(self._same_headers)
        opt_layout.addWidget(self._need_formulas)
        layout.addWidget(opt_box)

        self._rec_frame = QFrame()
        self._rec_frame.setObjectName("card")
        rec_layout = QVBoxLayout(self._rec_frame)
        self._rec_title = QLabel()
        self._rec_title.setWordWrap(True)
        self._rec_title.setStyleSheet("font-weight: 700; font-size: 14px;")
        self._rec_reason = QLabel()
        self._rec_reason.setWordWrap(True)
        self._rec_tips = QLabel()
        self._rec_tips.setWordWrap(True)
        self._rec_tips.setProperty("role", "hint")
        rec_layout.addWidget(QLabel("系統建議"))
        rec_layout.addWidget(self._rec_title)
        rec_layout.addWidget(self._rec_reason)
        rec_layout.addWidget(self._rec_tips)
        layout.addWidget(self._rec_frame)

        for btn in self._goal_group.buttons():
            btn.toggled.connect(self._refresh_advice)
        self._same_headers.toggled.connect(self._refresh_advice)
        self._need_formulas.toggled.connect(self._refresh_advice)
        self._refresh_advice()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("繼續合併精靈")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _goal_key(self) -> str:
        if self._goal_tabs.isChecked():
            return "move_tabs"
        if self._goal_sheets.isChecked():
            return "keep_sheets"
        return "stack_rows"

    def _refresh_advice(self) -> None:
        self._advice = advise_merge(
            file_count=self._file_count,
            goal=self._goal_key(),
            same_headers=self._same_headers.isChecked(),
            need_formulas=self._need_formulas.isChecked(),
        )
        self._chosen_mode = self._advice.recommended_mode
        conf = "信心：高" if self._advice.confidence == "high" else "信心：中"
        self._rec_title.setText(f"{self._advice.title}（{conf}）")
        self._rec_reason.setText(self._advice.reason)
        tips = "\n".join(f"• {t}" for t in self._advice.tips)
        self._rec_tips.setText(tips)

    def advice(self) -> MergeAdvice | None:
        return self._advice

    def recommended_mode(self) -> MergeModeChoice:
        return self._chosen_mode

    def use_app_merge(self) -> bool:
        return self.recommended_mode() != "excel_native"
