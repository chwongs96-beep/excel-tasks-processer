"""Persist and load column mapping presets as JSON files."""

from __future__ import annotations

import json
from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "mapping_presets"


def _ensure_dir() -> None:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def list_presets() -> list[str]:
    """Return available preset names (without .json extension)."""
    _ensure_dir()
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def load_preset(name: str) -> dict[str, str]:
    """Load a mapping preset by name."""
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到映射 preset：{name}")
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"preset 格式無效：{name}")
    return {str(k): str(v) for k, v in data.items()}


def save_preset(name: str, mapping: dict[str, str]) -> Path:
    """Save mapping preset; returns written path."""
    _ensure_dir()
    safe = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip()
    if not safe:
        raise ValueError("preset 名稱不可為空")
    path = PRESETS_DIR / f"{safe}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2)
    return path
