"""Optional progress reporting for long-running operations."""

from __future__ import annotations

from typing import Protocol


class ProgressReporter(Protocol):
    def start(self, index: int, label: str) -> None: ...

    def done(self, index: int) -> None: ...

    def log(self, text: str) -> None: ...
