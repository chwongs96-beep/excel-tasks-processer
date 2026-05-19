"""Compact session status row."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from app.application.import_session import ImportSession


class SessionBar(QFrame):
    """One-line session summary above the data preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sessionBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self._summary = QLabel("尚未匯入檔案")
        self._summary.setObjectName("sessionSummary")
        layout.addWidget(self._summary, stretch=1)

        self._mapping = self._chip("映射 —")
        self._watch = self._chip("監看 關")
        layout.addWidget(self._mapping)
        layout.addWidget(self._watch)

    @staticmethod
    def _chip(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "stat-chip")
        return label

    def refresh(self, session: ImportSession) -> None:
        n = len(session.files)
        if n == 0:
            self._summary.setText("尚未匯入檔案 — 請從左側「新增檔案」開始")
        else:
            names = ", ".join(f.path.name for f in session.files[:3])
            if n > 3:
                names += f" 等 {n} 個檔案"
            self._summary.setText(names)

        m = len(session.mapping)
        self._mapping.setText(f"映射 {m} 項" if m else "映射 未設定")

        if session.adjustment:
            self._summary.setText(
                self._summary.text() + f" ｜ 調整分錄：{session.adjustment.path.name}"
            )
        if session.watch_folder:
            self._watch.setText(f"監看 {Path(session.watch_folder).name}")
        else:
            self._watch.setText("監看 關")
