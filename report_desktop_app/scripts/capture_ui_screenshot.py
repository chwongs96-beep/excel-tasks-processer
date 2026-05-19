#!/usr/bin/env python3
"""Capture main window screenshot for README / docs (dev only)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.core.config import ensure_dirs
from app.core.logger import setup_logging
from app.ui.main_window import MainWindow
from app.ui.styles import apply_app_style


def main() -> int:
    out_dir = _ROOT.parent / "docs" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "desktop-ui-main.png"

    setup_logging()
    ensure_dirs()

    app = QApplication(sys.argv)
    apply_app_style(app)
    window = MainWindow()
    window.show()

    def capture() -> None:
        app.processEvents()
        window.repaint()
        app.processEvents()
        pixmap = window.grab()
        ok = pixmap.save(str(out_path))
        print(f"saved={ok} path={out_path} size={pixmap.width()}x{pixmap.height()}")
        app.quit()

    QTimer.singleShot(800, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
