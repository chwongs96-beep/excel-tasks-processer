"""Layout helpers."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


def horizontal_rule() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


def section_label(text: str) -> QWidget:
    from PySide6.QtWidgets import QLabel

    label = QLabel(text)
    label.setProperty("role", "section")
    return label
