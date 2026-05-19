"""Compare two Excel-derived tables (ledger vs system export)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from app.core.logger import get_logger
from app.core.range_spec import SourceRangeSpec
from app.core.reporting_bridge import ensure_reporting_package
from app.services.excel_reader import ExcelReaderService

ensure_reporting_package()

from reporting.core.safe_io import atomic_save_workbook, secure_output_path  # noqa: E402

logger = get_logger()


@dataclass
class ReconcileRequest:
    left_path: Path
    right_path: Path
    left_range: SourceRangeSpec
    right_range: SourceRangeSpec
    key_columns: list[str]
    amount_column: str | None = None
    tolerance: float = 0.01
    output_path: Path | None = None


@dataclass
class ReconcileResult:
    success: bool
    summary: dict[str, int] = field(default_factory=dict)
    only_left: pd.DataFrame = field(default_factory=pd.DataFrame)
    only_right: pd.DataFrame = field(default_factory=pd.DataFrame)
    amount_mismatch: pd.DataFrame = field(default_factory=pd.DataFrame)
    output_path: Path | None = None
    errors: list[str] = field(default_factory=list)


class ReconcileService:
    """Find rows only on one side or with differing amounts."""

    def __init__(self) -> None:
        self._reader = ExcelReaderService()

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        if len(request.key_columns) < 1:
            return ReconcileResult(success=False, errors=["請至少選擇一個對帳鍵欄位。"])

        try:
            left = self._reader.load_sheet(request.left_path, range_spec=request.left_range)
            right = self._reader.load_sheet(request.right_path, range_spec=request.right_range)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Reconcile load failed")
            return ReconcileResult(success=False, errors=[str(exc)])

        missing = [c for c in request.key_columns if c not in left.columns or c not in right.columns]
        if missing:
            return ReconcileResult(
                success=False,
                errors=[f"對帳鍵欄位不存在於兩邊資料：{', '.join(missing)}"],
            )

        if request.amount_column:
            if request.amount_column not in left.columns or request.amount_column not in right.columns:
                return ReconcileResult(
                    success=False,
                    errors=[f"金額欄「{request.amount_column}」不存在於兩邊資料。"],
                )

        left_norm = self._normalize_keys(left, request.key_columns)
        right_norm = self._normalize_keys(right, request.key_columns)

        merged = left_norm.merge(
            right_norm,
            on="_reconcile_key",
            how="outer",
            indicator=True,
            suffixes=("_左", "_右"),
        )

        only_left = merged[merged["_merge"] == "left_only"].copy()
        only_right = merged[merged["_merge"] == "right_only"].copy()
        both = merged[merged["_merge"] == "both"].copy()

        amount_mismatch = pd.DataFrame()
        if request.amount_column and not both.empty:
            left_amt = f"{request.amount_column}_左"
            right_amt = f"{request.amount_column}_右"
            if left_amt in both.columns and right_amt in both.columns:
                left_vals = pd.to_numeric(both[left_amt], errors="coerce").fillna(0)
                right_vals = pd.to_numeric(both[right_amt], errors="coerce").fillna(0)
                diff = (left_vals - right_vals).abs()
                amount_mismatch = both[diff > request.tolerance].copy()

        summary = {
            "左檔列數": len(left),
            "右檔列數": len(right),
            "僅左邊": len(only_left),
            "僅右邊": len(only_right),
            "鍵相符": len(both),
            "金額不符": len(amount_mismatch),
        }

        output_path: Path | None = None
        if request.output_path:
            try:
                output_path = secure_output_path(
                    request.output_path.parent,
                    request.output_path.name,
                )
                self._export_workbook(output_path, only_left, only_right, amount_mismatch)
            except Exception as exc:  # noqa: BLE001
                return ReconcileResult(
                    success=False,
                    summary=summary,
                    only_left=only_left,
                    only_right=only_right,
                    amount_mismatch=amount_mismatch,
                    errors=[f"匯出對帳結果失敗：{exc}"],
                )

        return ReconcileResult(
            success=True,
            summary=summary,
            only_left=only_left,
            only_right=only_right,
            amount_mismatch=amount_mismatch,
            output_path=output_path,
        )

    @staticmethod
    def _normalize_keys(frame: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
        work = frame.copy()
        parts = [
            work[col].astype(str).str.strip().fillna("")
            for col in key_columns
        ]
        work["_reconcile_key"] = parts[0]
        for part in parts[1:]:
            work["_reconcile_key"] = work["_reconcile_key"] + "\x1f" + part
        return work

    @staticmethod
    def _export_workbook(
        path: Path,
        only_left: pd.DataFrame,
        only_right: pd.DataFrame,
        amount_mismatch: pd.DataFrame,
    ) -> None:
        wb = Workbook()
        wb.remove(wb.active)
        sheets = [
            ("僅左邊", only_left),
            ("僅右邊", only_right),
            ("金額不符", amount_mismatch),
        ]
        for title, frame in sheets:
            ws = wb.create_sheet(title[:31])
            if frame.empty:
                ws.append(["（無資料）"])
                continue
            cols = [c for c in frame.columns if c != "_reconcile_key"]
            ws.append(cols)
            for row in frame[cols].itertuples(index=False, name=None):
                ws.append(list(row))
        atomic_save_workbook(wb, path)
