"""Resolve application paths for development and PyInstaller bundles."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) is True


def bundle_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def user_data_dir(app_name: str = "SecuritiesReporting") -> Path:
    """Writable directory for output, logs, and user templates."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    return base / app_name


def resolve_desktop_root() -> Path:
    return bundle_dir()


def resolve_repo_root(desktop_root: Path) -> Path:
    if is_frozen():
        return bundle_dir()
    return desktop_root.parent


def resolve_shared_config_dir(repo_root: Path, desktop_root: Path) -> Path:
    bundled = bundle_dir() / "config"
    if bundled.is_dir():
        return bundled
    shared = repo_root / "config"
    if shared.is_dir():
        return shared
    return desktop_root / "config"


def resolve_output_dir(desktop_root: Path) -> Path:
    if is_frozen():
        path = user_data_dir() / "output"
    else:
        path = desktop_root / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_templates_dir(desktop_root: Path) -> Path:
    if is_frozen():
        path = user_data_dir() / "templates"
    else:
        path = desktop_root / "app" / "templates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_logs_dir(desktop_root: Path) -> Path:
    if is_frozen():
        path = user_data_dir() / "logs"
    else:
        path = desktop_root / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
