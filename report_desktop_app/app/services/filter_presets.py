"""Save and load folder filename-filter presets."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.core import config
from app.core.file_name_filter import FileNameFilter

_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _preset_path(name: str) -> Path:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Preset 名稱不可為空。")
    if _INVALID_NAME.search(cleaned):
        raise ValueError("Preset 名稱含有不允許的字元。")
    config.FILE_FILTER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return config.FILE_FILTER_PRESETS_DIR / f"{cleaned}.json"


def list_presets() -> list[str]:
    config.FILE_FILTER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.stem for path in config.FILE_FILTER_PRESETS_DIR.glob("*.json"))


def load_preset(name: str) -> FileNameFilter:
    path = _preset_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"找不到關鍵字 preset：{name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"preset 格式錯誤：{name}")
    return FileNameFilter.from_dict(data)


def save_preset(name: str, rules: FileNameFilter) -> Path:
    path = _preset_path(name)
    path.write_text(
        json.dumps(rules.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
