"""Ctrl + mouse wheel UI zoom, with optional status bar controls."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

from app.ui import styles


class UiZoomController(QObject):
    """Scale application font globally, including Ctrl+wheel in child widgets."""

    DEFAULT_FACTOR = 1.0
    MIN_FACTOR = 0.75
    MAX_FACTOR = 1.8
    STEP = 0.05

    def __init__(self, app: QApplication, window: QWidget) -> None:
        super().__init__(window)
        self._app = app
        self._window = window
        base = app.font().pointSizeF()
        if base <= 0:
            base = 11.0
        self._base_point_size = base
        self._factor = styles.load_zoom_factor()
        self._callbacks: list[Callable[[float], None]] = []
        self._wheel_remainder = 0.0
        app.installEventFilter(self)
        self.apply()

    def factor(self) -> float:
        return self._factor

    def percent_label(self) -> str:
        return f"{int(round(self._factor * 100))}%"

    def on_changed(self, callback: Callable[[float], None]) -> None:
        self._callbacks.append(callback)

    def _notify(self) -> None:
        for callback in self._callbacks:
            callback(self._factor)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            wheel = event  # type: ignore[assignment]
            if wheel.modifiers() & Qt.KeyboardModifier.ControlModifier:
                target = obj if isinstance(obj, QWidget) else None
                if target is not None and not self._window.isAncestorOf(target) and target is not self._window:
                    return False
                self._handle_wheel_delta(
                    wheel.angleDelta().y(),
                    wheel.pixelDelta().y(),
                )
                return True
        return False

    def _handle_wheel_delta(self, angle_delta_y: int, pixel_delta_y: int) -> None:
        delta = angle_delta_y
        if delta == 0:
            delta = pixel_delta_y
        if delta == 0:
            return
        # Typical wheel notch is 120; touchpad often sends smaller deltas.
        self._wheel_remainder += delta / 120.0
        steps = int(self._wheel_remainder)
        if steps == 0:
            return
        self._wheel_remainder -= steps
        if steps > 0:
            for _ in range(steps):
                self.zoom_in()
        else:
            for _ in range(-steps):
                self.zoom_out()

    def zoom_in(self) -> None:
        self.set_factor(min(self.MAX_FACTOR, round(self._factor + self.STEP, 2)))

    def zoom_out(self) -> None:
        self.set_factor(max(self.MIN_FACTOR, round(self._factor - self.STEP, 2)))

    def reset(self) -> None:
        self.set_factor(self.DEFAULT_FACTOR)

    def set_percent(self, percent: int) -> None:
        self.set_factor(percent / 100.0)

    def set_factor(self, factor: float) -> None:
        self._factor = styles.save_zoom_factor(
            max(self.MIN_FACTOR, min(self.MAX_FACTOR, factor))
        )
        self.apply()

    def can_zoom_in(self) -> bool:
        return self._factor < self.MAX_FACTOR - 1e-6

    def can_zoom_out(self) -> bool:
        return self._factor > self.MIN_FACTOR + 1e-6

    def apply(self) -> None:
        font = QFont(self._app.font())
        font.setPointSizeF(self._base_point_size * self._factor)
        self._app.setFont(font)
        styles.refresh_stylesheet(self._app)
        self._notify()
