"""Visual workflow step indicator."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

STEPS = ("匯入", "映射", "驗證", "預覽", "產報")


class ClickableStepLabel(QLabel):
    clicked = Signal(int)

    def __init__(self, index: int, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)


class WorkflowBar(QFrame):
    """Horizontal stepper for the accounting workflow."""
    step_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        title = QLabel("工作流程")
        title.setObjectName("workflowTitle")
        layout.addWidget(title)

        self._labels: list[ClickableStepLabel] = []
        for i, name in enumerate(STEPS):
            if i > 0:
                arrow = QLabel("›")
                arrow.setObjectName("workflowArrow")
                layout.addWidget(arrow)
            label = ClickableStepLabel(i, f"{i + 1}. {name}")
            label.setProperty("role", "workflow-step")
            label.clicked.connect(self.step_clicked.emit)
            layout.addWidget(label)
            self._labels.append(label)
        layout.addStretch(1)

    def set_step(self, index: int) -> None:
        index = max(0, min(index, len(self._labels) - 1))
        for i, label in enumerate(self._labels):
            if i < index:
                role = "workflow-step-done"
            elif i == index:
                role = "workflow-step-active"
            else:
                role = "workflow-step"
            label.setProperty("role", role)
            label.style().unpolish(label)
            label.style().polish(label)
