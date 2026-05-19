"""Theme registry and stylesheet generation."""

from __future__ import annotations

from app.ui.styles import build_stylesheet, load_theme_id, save_theme_id
from app.ui.themes import (
    DEFAULT_THEME_ID,
    THEMES,
    get_theme,
    resolve_theme_id,
    theme_ids,
)


def test_three_bright_themes_registered() -> None:
    assert len(theme_ids()) == 3
    assert DEFAULT_THEME_ID == "bright_daylight"
    for tid in theme_ids():
        theme = get_theme(tid)
        # Sidebar should be light (high luminance)
        assert theme.sidebar_bg.lower() not in ("#1a2b42", "#2d3748", "#1e3a2f")


def test_build_stylesheet_contains_sidebar() -> None:
    for tid in theme_ids():
        qss = build_stylesheet(get_theme(tid))
        assert "QWidget#sidebar" in qss
        assert get_theme(tid).sidebar_bg in qss


def test_legacy_theme_ids_map_to_bright() -> None:
    assert resolve_theme_id("professional_blue") == "bright_daylight"
    assert resolve_theme_id("forest_ledger") == "bright_sky"


def test_unknown_theme_falls_back_to_default() -> None:
    assert get_theme("not-a-theme").id == DEFAULT_THEME_ID


def test_save_and_load_theme_id(tmp_path, monkeypatch) -> None:
    from PySide6.QtCore import QSettings

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))

    save_theme_id("bright_sky")
    assert load_theme_id() == "bright_sky"

    save_theme_id("professional_blue")
    assert load_theme_id() == "bright_daylight"
