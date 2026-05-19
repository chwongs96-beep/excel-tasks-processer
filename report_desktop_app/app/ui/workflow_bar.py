"""Visual workflow step indicator."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

STEPS = ("匯入", "映射", "驗證", "預覽", "產報")


class WorkflowBar(QFrame):
    """Horizontal stepper for the accounting workflow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        title = QLabel("工作流程")
        title.setObjectName("workflowTitle")
        layout.addWidget(title)

        self._labels: list[QLabel] = []
        for i, name in enumerate(STEPS):
            if i > 0:
                arrow = QLabel("›")
                arrow.setObjectName("workflowArrow")
                layout.addWidget(arrow)
            label = QLabel(f"{i + 1}. {name}")
            label.setProperty("role", "workflow-step")
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
