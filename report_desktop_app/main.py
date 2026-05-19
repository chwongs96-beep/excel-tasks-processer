#!/usr/bin/env python3
"""Desktop reporting application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure report_desktop_app root is on sys.path when run as `python main.py`
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtWidgets import QApplication

from app.core.config import APP_NAME, ensure_dirs
from app.core.logger import setup_logging
from app.ui.main_window import MainWindow
from app.ui.styles import apply_app_style


def main() -> int:
    setup_logging()
    ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("InternalAccounting")
    apply_app_style(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
