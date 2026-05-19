"""Ctrl + mouse wheel UI zoom, with optional toolbar buttons."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget


class UiZoomController(QObject):
    """Scale application font; default slightly enlarged for readability."""

    BASE_POINT_SIZE = 14.0
    DEFAULT_FACTOR = 1.1
    MIN_FACTOR = 0.85
    MAX_FACTOR = 1.6
    STEP = 0.08

    def __init__(self, app: QApplication, window: QWidget) -> None:
        super().__init__(window)
        self._app = app
        self._window = window
        self._factor = self.DEFAULT_FACTOR
        self._callbacks: list[object] = []
        window.installEventFilter(self)
        self.apply()

    def factor(self) -> float:
        return self._factor

    def percent_label(self) -> str:
        return f"{int(round(self._factor * 100))}%"

    def on_changed(self, callback) -> None:
        self._callbacks.append(callback)

    def _notify(self) -> None:
        for callback in self._callbacks:
            callback(self._factor)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self._window and event.type() == QEvent.Type.Wheel:
            wheel = event  # type: ignore[assignment]
            if wheel.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if wheel.angleDelta().y() > 0:
                    self.zoom_in()
                elif wheel.angleDelta().y() < 0:
                    self.zoom_out()
                return True
        return False

    def zoom_in(self) -> None:
        self.set_factor(min(self.MAX_FACTOR, round(self._factor + self.STEP, 2)))

    def zoom_out(self) -> None:
        self.set_factor(max(self.MIN_FACTOR, round(self._factor - self.STEP, 2)))

    def reset(self) -> None:
        self.set_factor(self.DEFAULT_FACTOR)

    def set_factor(self, factor: float) -> None:
        self._factor = max(self.MIN_FACTOR, min(self.MAX_FACTOR, factor))
        self.apply()

    def apply(self) -> None:
        font = QFont(self._app.font())
        font.setPointSizeF(self.BASE_POINT_SIZE * self._factor)
        self._app.setFont(font)
        self._notify()
