"""Load and save column mapping presets (shared with Streamlit via reporting)."""

from __future__ import annotations

from pathlib import Path

from app.core.reporting_bridge import ensure_reporting_package

ensure_reporting_package()

from reporting.mapping.presets import (  # noqa: E402
    list_presets as _list_presets,
    load_preset as _load_preset,
    save_preset as _save_preset,
)


def list_presets() -> list[str]:
    return _list_presets()


def load_preset(name: str) -> dict[str, str]:
    return _load_preset(name)


def save_preset(name: str, mapping: dict[str, str]) -> Path:
    return _save_preset(name, mapping)
