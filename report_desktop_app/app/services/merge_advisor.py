"""Recommend the smartest merge approach for multi-file Excel work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MergeModeChoice = Literal["single_sheet", "one_sheet_per_file", "excel_native"]


@dataclass(frozen=True)
class MergeAdvice:
    """Recommendation shown before running the consolidate wizard."""

    recommended_mode: MergeModeChoice
    title: str
    reason: str
    confidence: Literal["high", "medium"]
    tips: tuple[str, ...]


def advise_merge(
    *,
    file_count: int,
    goal: str,
    same_headers: bool,
    need_formulas: bool,
) -> MergeAdvice:
    """
    Pick the best approach from user answers.

    goal: ``stack_rows`` | ``keep_sheets`` | ``move_tabs``
    """
    if goal == "move_tabs" or need_formulas:
        return MergeAdvice(
            recommended_mode="excel_native",
            title="建議：Excel 內建「移動或複製工作表」",
            reason=(
                "您需要保留完整分頁、公式或格式。"
                "本工具合併會依「資料範圍」重寫儲存格內容，較適合明細列資料，"
                "不適合原樣搬移整張工作表。"
            ),
            confidence="high",
            tips=(
                "來源檔與目標檔同時開啟 → 工作表標籤右鍵 → 移動或複製…",
                "要保留來源分頁請勾選「建立副本」。",
            ),
        )

    if goal == "keep_sheets" or file_count <= 1:
        mode: MergeModeChoice = "one_sheet_per_file"
        reason = (
            "每個來源檔各成一個工作表，便於分檔對照與覆核。"
            if goal == "keep_sheets"
            else "僅一個檔案時，可輸出為單一工作表或保留原分頁。"
        )
        return MergeAdvice(
            recommended_mode=mode,
            title="建議：本工具 →「每個來源一個工作表」",
            reason=reason,
            confidence="high",
            tips=(
                "合併前請為每個檔案設定正確的「資料範圍」。",
                "輸出檔工作表名稱以檔名為準（過長會自動截短）。",
            ),
        )

    # stack_rows — default for accounting detail
    if same_headers:
        return MergeAdvice(
            recommended_mode="single_sheet",
            title="建議：本工具 →「合併到單一工作表」（最省事）",
            reason=(
                f"您有 {file_count} 個來源且欄位標題一致，"
                "適合垂直堆疊成一份總明細；系統會自動加上 _source_file 欄標記來源。"
            ),
            confidence="high",
            tips=(
                "合併後可勾選「自動匯入」再接欄位映射與產報。",
                "若某檔標題列不同，請先統一或改選「每個來源一個工作表」。",
            ),
        )

    return MergeAdvice(
        recommended_mode="one_sheet_per_file",
        title="建議：本工具 →「每個來源一個工作表」",
        reason=(
            "各檔欄位標題不一致，先分工作表合併較安全；"
            "之後可逐表檢查，或統一欄名後再手動合併。"
        ),
        confidence="medium",
        tips=(
            "亦可先統一各檔標題列，再改用「單一工作表」模式。",
            "合併完成後使用「欄位映射」對齊標準會計欄位。",
        ),
    )
