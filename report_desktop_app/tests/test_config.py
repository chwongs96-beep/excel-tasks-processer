"""Tests for path configuration."""

from __future__ import annotations

from app.core import config


def test_desktop_root_is_report_desktop_app() -> None:
    assert config.DESKTOP_ROOT.name == "report_desktop_app"


def test_ensure_dirs_creates_output() -> None:
    config.ensure_dirs()
    assert config.OUTPUT_DIR.is_dir()
