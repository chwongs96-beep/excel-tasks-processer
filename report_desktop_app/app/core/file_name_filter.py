"""Filename keyword rules for folder discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileNameFilter:
    """
    Match Excel filenames by substring rules.

    - ``include_any``: if non-empty, name must contain at least one keyword (OR).
    - ``exclude_any``: if name contains any keyword, file is skipped.
    """

    include_any: tuple[str, ...] = ()
    exclude_any: tuple[str, ...] = ()
    case_insensitive: bool = True
    range_preset: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "include_keywords": list(self.include_any),
            "exclude_keywords": list(self.exclude_any),
            "case_insensitive": self.case_insensitive,
            "range_preset": self.range_preset,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FileNameFilter:
        def _keywords(key: str) -> tuple[str, ...]:
            raw = data.get(key) or []
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.replace(";", ",").split(",")]
            elif isinstance(raw, list):
                parts = [str(p).strip() for p in raw]
            else:
                parts = []
            return tuple(p for p in parts if p)

        preset = data.get("range_preset")
        return cls(
            include_any=_keywords("include_keywords"),
            exclude_any=_keywords("exclude_keywords"),
            case_insensitive=bool(data.get("case_insensitive", True)),
            range_preset=str(preset).strip() if preset else None,
        )

    @classmethod
    def empty(cls) -> FileNameFilter:
        return cls()

    def summary(self) -> str:
        parts: list[str] = []
        if self.include_any:
            parts.append("包含：" + " / ".join(self.include_any))
        if self.exclude_any:
            parts.append("排除：" + " / ".join(self.exclude_any))
        if self.range_preset:
            parts.append(f"範圍 preset：{self.range_preset}")
        return "；".join(parts) if parts else "（無關鍵字篩選，匯入全部 Excel）"

    def matches(self, path: Path) -> bool:
        name = path.name
        probe = name.casefold() if self.case_insensitive else name

        for word in self.exclude_any:
            token = word.casefold() if self.case_insensitive else word
            if token and token in probe:
                return False

        if not self.include_any:
            return True

        for word in self.include_any:
            token = word.casefold() if self.case_insensitive else word
            if token and token in probe:
                return True
        return False


@dataclass
class FolderScanResult:
    """Outcome of scanning a folder with a filename filter."""

    folder: Path
    matched: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)

    @property
    def all_excel(self) -> list[Path]:
        return [*self.matched, *self.skipped]
