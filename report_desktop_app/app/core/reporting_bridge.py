"""Ensure parent repo reporting package is importable."""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import REPO_ROOT

_REPO_ON_PATH = False


def ensure_reporting_package() -> None:
    global _REPO_ON_PATH  # noqa: PLW0603
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
        _REPO_ON_PATH = True
