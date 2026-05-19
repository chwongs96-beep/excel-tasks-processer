"""Background task runner — keeps the UI responsive during heavy work."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from PySide6.QtCore import QObject, QThread, Signal

T = TypeVar("T")


class _Worker(QObject):
    """Runs a callable on a background thread."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, func: Callable[[], T]) -> None:
        super().__init__()
        self._func = func

    def run(self) -> None:
        try:
            self.finished.emit(self._func())
        except Exception as exc:  # noqa: BLE001 — surfaced to UI
            self.failed.emit(str(exc))


class BackgroundTaskRunner(QObject):
    """
    Submit callables to a QThread.

    UI connects to busy_changed, completed, and failed.
  """

    busy_changed = Signal(bool)
    completed = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._current_task: str | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def submit(self, task_name: str, func: Callable[[], T]) -> bool:
        """
        Run ``func`` on a worker thread.

        Returns False if a task is already running.
        """
        if self.is_busy:
            return False

        self._current_task = task_name
        self.busy_changed.emit(True)

        self._thread = QThread()
        self._worker = _Worker(func)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

        self._thread.start()
        return True

    def _on_finished(self, result: object) -> None:
        name = self._current_task or ""
        self.completed.emit(name, result)

    def _on_failed(self, message: str) -> None:
        name = self._current_task or ""
        self.failed.emit(name, message)

    def _cleanup(self) -> None:
        self._thread = None
        self._worker = None
        self._current_task = None
        self.busy_changed.emit(False)
