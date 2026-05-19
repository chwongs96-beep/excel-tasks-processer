"""Merge advisor recommendations."""

from __future__ import annotations

from app.services.merge_advisor import advise_merge


def test_stack_rows_same_headers_recommends_single_sheet() -> None:
    advice = advise_merge(
        file_count=6,
        goal="stack_rows",
        same_headers=True,
        need_formulas=False,
    )
    assert advice.recommended_mode == "single_sheet"


def test_different_headers_recommends_per_file_sheet() -> None:
    advice = advise_merge(
        file_count=6,
        goal="stack_rows",
        same_headers=False,
        need_formulas=False,
    )
    assert advice.recommended_mode == "one_sheet_per_file"


def test_need_formulas_recommends_excel_native() -> None:
    advice = advise_merge(
        file_count=3,
        goal="stack_rows",
        same_headers=True,
        need_formulas=True,
    )
    assert advice.recommended_mode == "excel_native"
