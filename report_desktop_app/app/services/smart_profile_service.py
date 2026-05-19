"""Persist and suggest mapping profiles from user history."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core import config


def _normalize(text: str) -> str:
    return config.normalize_header(text)


def _column_fingerprint(columns: list[str]) -> str:
    normalized = sorted(_normalize(item) for item in columns if item)
    payload = "|".join(normalized)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()  # noqa: S324


def _filename_pattern(filename: str) -> str:
    stem = Path(filename).stem
    norm = _normalize(stem)
    norm = re.sub(r"\d+", "{n}", norm)
    return norm


@dataclass(frozen=True)
class ProfileSuggestion:
    mapping: dict[str, str]
    confidence: float
    reason: str


class SmartProfileService:
    """Read/write smart mapping profiles under local data dir."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (config.DATA_DIR / "smart_profiles.json")

    def suggest(self, *, filename: str, source_columns: list[str]) -> ProfileSuggestion | None:
        doc = self._load()
        items = doc.get("profiles", [])
        if not isinstance(items, list):
            return None

        fp = _column_fingerprint(source_columns)
        pattern = _filename_pattern(filename)

        # 1) Exact schema fingerprint match.
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if raw.get("column_fingerprint") != fp:
                continue
            mapping = self._filter_mapping(raw.get("mapping"), source_columns)
            if mapping:
                return ProfileSuggestion(
                    mapping=mapping,
                    confidence=0.95,
                    reason="欄位結構完全一致（歷史記錄）",
                )

        # 2) Filename pattern match as fallback.
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if raw.get("filename_pattern") != pattern:
                continue
            mapping = self._filter_mapping(raw.get("mapping"), source_columns)
            if mapping:
                return ProfileSuggestion(
                    mapping=mapping,
                    confidence=0.75,
                    reason="檔名樣式一致（歷史記錄）",
                )
        return None

    def record(self, *, filename: str, source_columns: list[str], mapping: dict[str, str]) -> None:
        clean_mapping = self._filter_mapping(mapping, source_columns)
        if not clean_mapping:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        doc = self._load()
        items = doc.get("profiles", [])
        if not isinstance(items, list):
            items = []
        fp = _column_fingerprint(source_columns)
        pattern = _filename_pattern(filename)
        now = datetime.now(timezone.utc).isoformat()

        target: dict | None = None
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if raw.get("column_fingerprint") == fp and raw.get("filename_pattern") == pattern:
                target = raw
                break
        if target is None:
            target = {
                "filename_pattern": pattern,
                "column_fingerprint": fp,
                "mapping": clean_mapping,
                "hits": 1,
                "last_used": now,
            }
            items.append(target)
        else:
            target["mapping"] = clean_mapping
            target["hits"] = int(target.get("hits", 0)) + 1
            target["last_used"] = now

        doc["profiles"] = items
        self._path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> dict:
        if not self._path.is_file():
            return {"profiles": []}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {"profiles": []}
        if not isinstance(data, dict):
            return {"profiles": []}
        return data

    @staticmethod
    def _filter_mapping(mapping: object, source_columns: list[str]) -> dict[str, str]:
        if not isinstance(mapping, dict):
            return {}
        allowed = set(source_columns)
        out: dict[str, str] = {}
        for canonical, source in mapping.items():
            if not isinstance(canonical, str) or not isinstance(source, str):
                continue
            if canonical and source and source in allowed:
                out[canonical] = source
        return out
