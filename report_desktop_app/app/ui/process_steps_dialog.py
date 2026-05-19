"""Modal progress window listing processing steps (unlimited count)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProcessTracker(QObject):
    """Thread-safe step updates via Qt signals (emit from worker thread)."""

    step_active = Signal(int, str)
    step_done = Signal(int)
    detail = Signal(str)

    def start(self, index: int, label: str) -> None:
        self.step_active.emit(index, label)

    def done(self, index: int) -> None:
        self.step_done.emit(index)

    def log(self, text: str) -> None:
        self.detail.emit(text)


class ProcessStepsDialog(QDialog):
    """Shows numbered steps: pending → active → done. Supports any number of steps."""

    _ROW_PX = 28
    _MIN_H = 280
    _MAX_H = 640

    def __init__(self, steps: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("處理進度")
        self.setModal(True)
        self.resize(520, 400)
        self._step_labels: list[str] = []
        self._finished = False

        layout = QVBoxLayout(self)
        self._header = QLabel()
        layout.addWidget(self._header)

        self._list = QListWidget()
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.AlwaysOff)
        font = self._list.font()
        font.setPointSize(max(10, font.pointSize() - 1))
        self._list.setFont(font)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._list)
        scroll.setMinimumHeight(160)
        layout.addWidget(scroll, stretch=1)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(110)
        self._detail.setPlaceholderText("執行紀錄…")
        layout.addWidget(self._detail)

        self._close_btn = QPushButton("關閉")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.accept)
        layout.addWidget(self._close_btn)

        initial = list(steps or [])
        for i, name in enumerate(initial):
            self._append_step_row(i, name)

        self._resize_for_count(max(1, self._list.count()))
        self._update_header()

    def bind_tracker(self, tracker: ProcessTracker) -> None:
        tracker.step_active.connect(self._on_step_active)
        tracker.step_done.connect(self._on_step_done)
        tracker.detail.connect(self._append_detail)

    def _update_header(self) -> None:
        n = self._list.count()
        self._header.setText(f"請稍候，正在依序執行（共 {n} 個步驟，可捲動查看）：")

    def _append_step_row(self, index: int, label: str) -> None:
        while len(self._step_labels) < index:
            self._step_labels.append(f"步驟 {len(self._step_labels) + 1}")
            self._list.addItem(
                QListWidgetItem(f"○  {len(self._step_labels)}. {self._step_labels[-1]}")
            )
        if len(self._step_labels) == index:
            self._step_labels.append(label)
            self._list.addItem(QListWidgetItem(f"○  {index + 1}. {label}"))
        else:
            self._step_labels[index] = label
            self._list.item(index).setText(f"○  {index + 1}. {label}")

    def _ensure_step(self, index: int, label: str) -> None:
        if index >= len(self._step_labels):
            self._append_step_row(index, label)
            self._resize_for_count(self._list.count())
            self._update_header()
        else:
            self._step_labels[index] = label

    def _resize_for_count(self, count: int) -> None:
        list_h = min(max(count * self._ROW_PX + 12, 120), 420)
        self._list.setMinimumHeight(list_h)
        dialog_h = min(max(self._MIN_H + list_h - 160, self._MIN_H), self._MAX_H)
        screen = QApplication.primaryScreen()
        if screen is not None:
            max_h = int(screen.availableGeometry().height() * 0.85)
            dialog_h = min(dialog_h, max_h)
        self.resize(self.width(), dialog_h)

    def _scroll_to(self, index: int) -> None:
        item = self._list.item(index)
        if item is not None:
            self._list.scrollToItem(item)

    def _on_step_active(self, index: int, label: str) -> None:
        self._ensure_step(index, label)
        if 0 <= index < self._list.count():
            self._list.item(index).setText(f"▶  {index + 1}. {label}")
            self._scroll_to(index)
        self._append_detail(f"開始：{label}")

    def _on_step_done(self, index: int) -> None:
        if 0 <= index < self._list.count():
            name = self._step_labels[index] if index < len(self._step_labels) else ""
            self._list.item(index).setText(f"✓  {index + 1}. {name}")

    def _append_detail(self, text: str) -> None:
        self._detail.append(text)

    def finish(self, success: bool, message: str = "") -> None:
        if self._finished:
            return
        self._finished = True
        if message:
            level = "完成" if success else "失敗"
            self._append_detail(f"{level}：{message}")
        self._close_btn.setEnabled(True)
        self.setWindowTitle("處理完成" if success else "處理失敗")
