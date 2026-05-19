"""Save/load reusable execution setups (report type + paths + date spec)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.core import config
from app.core.schemas import DateSpec, ReportType

_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _iso_to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


@dataclass(frozen=True)
class SetupPreset:
    name: str
    report_type: ReportType
    template_path: str
    output_dir: str
    trade_date: str | None = None
    week_start: str | None = None
    week_end: str | None = None
    month: str | None = None
    mapping_preset: str | None = None
    range_preset: str | None = None
    filter_preset: str | None = None

    @staticmethod
    def from_runtime(
        *,
        name: str,
        report_type: ReportType,
        template_path: Path,
        output_dir: Path,
        date_spec: DateSpec,
    ) -> "SetupPreset":
        return SetupPreset(
            name=name,
            report_type=report_type,
            template_path=str(template_path),
            output_dir=str(output_dir),
            trade_date=_date_to_iso(date_spec.trade_date),
            week_start=_date_to_iso(date_spec.week_start),
            week_end=_date_to_iso(date_spec.week_end),
            month=_date_to_iso(date_spec.month),
            mapping_preset=None,
            range_preset=None,
            filter_preset=None,
        )

    def to_date_spec(self) -> DateSpec:
        return DateSpec(
            report_type=self.report_type,
            trade_date=_iso_to_date(self.trade_date),
            week_start=_iso_to_date(self.week_start),
            week_end=_iso_to_date(self.week_end),
            month=_iso_to_date(self.month),
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "report_type": self.report_type,
            "template_path": self.template_path,
            "output_dir": self.output_dir,
            "trade_date": self.trade_date,
            "week_start": self.week_start,
            "week_end": self.week_end,
            "month": self.month,
            "mapping_preset": self.mapping_preset,
            "range_preset": self.range_preset,
            "filter_preset": self.filter_preset,
        }

    @staticmethod
    def from_dict(data: dict) -> "SetupPreset":
        report_type = str(data.get("report_type", "daily"))
        if report_type not in {"daily", "weekly", "monthly"}:
            raise ValueError("report_type 必須為 daily / weekly / monthly")
        return SetupPreset(
            name=str(data.get("name", "")),
            report_type=report_type,  # type: ignore[arg-type]
            template_path=str(data.get("template_path", "")),
            output_dir=str(data.get("output_dir", "")),
            trade_date=(str(data["trade_date"]) if data.get("trade_date") else None),
            week_start=(str(data["week_start"]) if data.get("week_start") else None),
            week_end=(str(data["week_end"]) if data.get("week_end") else None),
            month=(str(data["month"]) if data.get("month") else None),
            mapping_preset=(str(data["mapping_preset"]) if data.get("mapping_preset") else None),
            range_preset=(str(data["range_preset"]) if data.get("range_preset") else None),
            filter_preset=(str(data["filter_preset"]) if data.get("filter_preset") else None),
        )


def _preset_path(name: str) -> Path:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Setup 名稱不可為空。")
    if _INVALID_NAME.search(cleaned):
        raise ValueError("Setup 名稱含有不允許的字元。")
    config.SETUP_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return config.SETUP_PRESETS_DIR / f"{cleaned}.json"


def list_presets() -> list[str]:
    config.SETUP_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.stem for path in config.SETUP_PRESETS_DIR.glob("*.json"))


def load_preset(name: str) -> SetupPreset:
    path = _preset_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"找不到 setup：{name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"setup 格式錯誤：{name}")
    preset = SetupPreset.from_dict(data)
    if not preset.name:
        preset = SetupPreset(
            name=name,
            report_type=preset.report_type,
            template_path=preset.template_path,
            output_dir=preset.output_dir,
            trade_date=preset.trade_date,
            week_start=preset.week_start,
            week_end=preset.week_end,
            month=preset.month,
            mapping_preset=preset.mapping_preset,
            range_preset=preset.range_preset,
            filter_preset=preset.filter_preset,
        )
    return preset


def save_preset(preset: SetupPreset) -> Path:
    path = _preset_path(preset.name)
    path.write_text(
        json.dumps(preset.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def delete_preset(name: str) -> None:
    path = _preset_path(name)
    if path.exists():
        path.unlink()
