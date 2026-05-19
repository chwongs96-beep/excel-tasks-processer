"""Suggest reconcile keys from column headers and schema aliases."""

from __future__ import annotations

from app.core import config


def suggest_key_columns(left_columns: list[str], right_columns: list[str]) -> list[str]:
    """Return common columns that look like good reconcile keys."""
    common = set(left_columns) & set(right_columns)
    if not common:
        return []

    schema = config.load_schema_config()
    scored: list[tuple[int, str]] = []

    norm_map = {config.normalize_header(c): c for c in common}

    priority_fields = (
        "trade_date",
        "account_id",
        "symbol",
        "description",
        "currency",
    )

    for field_name in priority_fields:
        if field_name in common:
            scored.append((0, field_name))
            continue
        field_def = next((f for f in schema.fields if f.name == field_name), None)
        if not field_def:
            continue
        for alias in field_def.aliases:
            key = config.normalize_header(alias)
            if key in norm_map:
                scored.append((1, norm_map[key]))

    for col in common:
        low = col.lower()
        if "date" in low or "日期" in col:
            scored.append((2, col))
        if "account" in low or "帳" in col or "戶" in col:
            scored.append((3, col))
        if "symbol" in low or "券" in col or "代號" in col:
            scored.append((4, col))

    seen: set[str] = set()
    ordered: list[str] = []
    for _, col in sorted(scored, key=lambda x: x[0]):
        if col not in seen:
            seen.add(col)
            ordered.append(col)
    return ordered[:5] if ordered else sorted(common)[:3]


def suggest_amount_column(columns: list[str]) -> str | None:
    for col in columns:
        if col in config.NUMERIC_COLUMNS:
            return col
        low = col.lower()
        if "amount" in low or "金額" in col or col in ("debit", "credit", "借方", "貸方"):
            return col
    return None
