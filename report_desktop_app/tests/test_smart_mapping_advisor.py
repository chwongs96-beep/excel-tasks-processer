"""Tests for smart mapping advisor."""

from __future__ import annotations

from app.services.smart_mapping_advisor import SmartMappingAdvisor


def test_suggest_prefers_alias_match() -> None:
    advisor = SmartMappingAdvisor(suggest_threshold=0.4)
    suggestions = advisor.suggest(
        source_columns=["交易日期", "帳號", "成交金額"],
        canonical_fields=("trade_date", "account_id", "amount"),
        aliases={
            "trade_date": ("交易日期", "日期"),
            "account_id": ("帳號", "帳戶"),
            "amount": ("成交金額", "金額"),
        },
    )
    assert suggestions["trade_date"].source_column == "交易日期"
    assert suggestions["account_id"].source_column == "帳號"
    assert suggestions["amount"].source_column == "成交金額"
    assert suggestions["amount"].score >= 0.9


def test_suggest_uses_one_to_one_assignment() -> None:
    advisor = SmartMappingAdvisor(suggest_threshold=0.2)
    suggestions = advisor.suggest(
        source_columns=["trade_date", "trade_dt"],
        canonical_fields=("trade_date", "settle_date"),
        aliases={
            "trade_date": ("trade_dt",),
            "settle_date": ("settle_dt", "trade_dt"),
        },
    )
    # same source column should not be assigned to both canonical fields
    used = {item.source_column for item in suggestions.values()}
    assert len(used) == len(suggestions)


def test_auto_apply_respects_threshold() -> None:
    advisor = SmartMappingAdvisor(auto_apply_threshold=0.9, suggest_threshold=0.3)
    mapping = advisor.auto_apply(
        source_columns=["交易日期", "帳號", "unknown_col"],
        canonical_fields=("trade_date", "account_id", "amount"),
        aliases={
            "trade_date": ("交易日期",),
            "account_id": ("帳號",),
            "amount": ("金額",),
        },
    )
    assert mapping["trade_date"] == "交易日期"
    assert mapping["account_id"] == "帳號"
    assert "amount" not in mapping
