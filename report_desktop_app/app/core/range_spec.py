"""Excel source range selection for partial sheet import."""

from __future__ import annotations

import re
from dataclasses import dataclass

from openpyxl.utils import column_index_from_string, get_column_letter
_CELL_RANGE_RE = re.compile(
    r"^([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)$",
    re.IGNORECASE,
)


@dataclass
class SourceRangeSpec:
    """
    Which part of a workbook sheet to read.

    If ``excel_range`` is set (e.g. ``B2:H500``), it overrides row/column bounds.
    Row numbers are 1-based (Excel style).
    """

    sheet: str | None = None
    header_row: int = 1
    start_row: int | None = None
    end_row: int | None = None
    start_column: str | None = None
    end_column: str | None = None
    excel_range: str | None = None

    @classmethod
    def default(cls) -> SourceRangeSpec:
        return cls()

    def to_dict(self) -> dict[str, object]:
        return {
            "sheet": self.sheet,
            "header_row": self.header_row,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "start_column": self.start_column,
            "end_column": self.end_column,
            "excel_range": self.excel_range,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SourceRangeSpec:
        def _opt_int(key: str) -> int | None:
            value = data.get(key)
            if value is None or value == "":
                return None
            return int(value)

        sheet = data.get("sheet")
        return cls(
            sheet=str(sheet) if sheet else None,
            header_row=int(data.get("header_row", 1)),
            start_row=_opt_int("start_row"),
            end_row=_opt_int("end_row"),
            start_column=str(data["start_column"]) if data.get("start_column") else None,
            end_column=str(data["end_column"]) if data.get("end_column") else None,
            excel_range=str(data["excel_range"]) if data.get("excel_range") else None,
        )

    def summary(self) -> str:
        if self.excel_range:
            sheet = self.sheet or "使用中工作表"
            return f"{sheet} ! {self.excel_range}"
        parts = [self.sheet or "使用中工作表"]
        if self.start_row or self.end_row:
            parts.append(f"列 {self.start_row or self.header_row + 1}–{self.end_row or '末'}")
        if self.start_column or self.end_column:
            parts.append(f"欄 {self.start_column or 'A'}–{self.end_column or '末'}")
        return " ".join(parts)

    def resolved_bounds(self) -> tuple[int, int, int, int, int]:
        """
        Return (header_row, min_row, max_row, min_col, max_col) all 1-based inclusive.
        """
        if self.excel_range:
            parsed = parse_excel_range(self.excel_range)
            if parsed is None:
                raise ValueError(f"無效的範圍：{self.excel_range}")
            min_col, min_row, max_col, max_row = parsed
            header = min_row if min_row > 0 else 1
            return header, min_row, max_row, min_col, max_col

        header = max(1, self.header_row)
        min_row = self.start_row if self.start_row is not None else header
        max_row = self.end_row if self.end_row is not None else 1_000_000
        min_col = column_index_from_string(self.start_column) if self.start_column else 1
        max_col = (
            column_index_from_string(self.end_column)
            if self.end_column
            else 256
        )
        return header, min_row, max_row, min_col, max_col


def parse_excel_range(text: str) -> tuple[int, int, int, int] | None:
    """Parse ``A1:H100`` → (min_col, min_row, max_col, max_row)."""
    cleaned = text.strip().replace("$", "")
    match = _CELL_RANGE_RE.match(cleaned)
    if not match:
        return None
    col_a, row_a, col_b, row_b = match.groups()
    min_col = column_index_from_string(col_a.upper())
    max_col = column_index_from_string(col_b.upper())
    min_row = int(row_a)
    max_row = int(row_b)
    if min_row > max_row:
        min_row, max_row = max_row, min_row
    if min_col > max_col:
        min_col, max_col = max_col, min_col
    return min_col, min_row, max_col, max_row


def column_letters_for_index(index: int) -> str:
    return get_column_letter(index)
