"""Rule-based advisor for canonical-to-source mapping suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.core import config


def _normalize(text: str) -> str:
    return config.normalize_header(text).replace("-", "_")


def _tokens(text: str) -> set[str]:
    norm = _normalize(text)
    return {token for token in norm.split("_") if token}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass(frozen=True)
class MappingSuggestion:
    canonical_field: str
    source_column: str
    score: float
    reasons: tuple[str, ...]


class SmartMappingAdvisor:
    """Generate mapping suggestions from header/alias similarity."""

    def __init__(
        self,
        *,
        auto_apply_threshold: float = 0.85,
        suggest_threshold: float = 0.60,
    ) -> None:
        self.auto_apply_threshold = auto_apply_threshold
        self.suggest_threshold = suggest_threshold

    def suggest(
        self,
        *,
        source_columns: list[str],
        canonical_fields: tuple[str, ...] | None = None,
        aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> dict[str, MappingSuggestion]:
        if not source_columns:
            return {}
        schema = config.load_schema_config()
        fields = canonical_fields or schema.canonical_fields
        alias_map = aliases or schema.column_aliases

        scores: list[tuple[float, str, str, tuple[str, ...]]] = []
        for canonical in fields:
            for source in source_columns:
                score, reasons = self._score_pair(
                    canonical=canonical,
                    source=source,
                    aliases=alias_map.get(canonical, ()),
                )
                if score >= self.suggest_threshold:
                    scores.append((score, canonical, source, reasons))

        # Greedy one-to-one assignment: highest score first.
        scores.sort(key=lambda item: item[0], reverse=True)
        picked_fields: set[str] = set()
        picked_sources: set[str] = set()
        result: dict[str, MappingSuggestion] = {}
        for score, canonical, source, reasons in scores:
            if canonical in picked_fields or source in picked_sources:
                continue
            picked_fields.add(canonical)
            picked_sources.add(source)
            result[canonical] = MappingSuggestion(
                canonical_field=canonical,
                source_column=source,
                score=round(score, 3),
                reasons=reasons,
            )
        return result

    def auto_apply(
        self,
        *,
        source_columns: list[str],
        canonical_fields: tuple[str, ...] | None = None,
        aliases: dict[str, tuple[str, ...]] | None = None,
    ) -> dict[str, str]:
        suggestions = self.suggest(
            source_columns=source_columns,
            canonical_fields=canonical_fields,
            aliases=aliases,
        )
        mapping: dict[str, str] = {}
        for canonical, suggestion in suggestions.items():
            if suggestion.score >= self.auto_apply_threshold:
                mapping[canonical] = suggestion.source_column
        return mapping

    def _score_pair(
        self,
        *,
        canonical: str,
        source: str,
        aliases: tuple[str, ...],
    ) -> tuple[float, tuple[str, ...]]:
        canonical_norm = _normalize(canonical)
        source_norm = _normalize(source)
        alias_norms = {_normalize(alias) for alias in aliases}
        reasons: list[str] = []

        if source_norm == canonical_norm:
            reasons.append("欄名完全相同")
            return 1.0, tuple(reasons)
        if source_norm in alias_norms:
            reasons.append("符合 schema 別名")
            return 0.95, tuple(reasons)

        ratio = SequenceMatcher(None, canonical_norm, source_norm).ratio()
        token_score = _jaccard(_tokens(canonical), _tokens(source))
        alias_ratio = 0.0
        for alias in alias_norms:
            alias_ratio = max(alias_ratio, SequenceMatcher(None, alias, source_norm).ratio())
        alias_token = 0.0
        src_tokens = _tokens(source)
        for alias in aliases:
            alias_token = max(alias_token, _jaccard(_tokens(alias), src_tokens))

        score = max(
            0.50 * ratio + 0.25 * token_score + 0.25 * alias_ratio,
            0.35 * ratio + 0.15 * token_score + 0.50 * alias_token,
        )
        if alias_ratio >= 0.8 or alias_token >= 0.8:
            reasons.append("接近 schema 別名")
        if ratio >= 0.75:
            reasons.append("欄名相似")
        if token_score >= 0.5:
            reasons.append("關鍵字重疊")
        if not reasons:
            reasons.append("字面相似度")

        return min(score, 0.94), tuple(reasons)


def from_config() -> SmartMappingAdvisor:
    cfg = config.load_smart_mode_config()
    advisor_cfg = cfg.get("advisor", {})
    auto = float(advisor_cfg.get("auto_apply_threshold", 0.85))
    suggest = float(advisor_cfg.get("suggest_threshold", 0.60))
    return SmartMappingAdvisor(
        auto_apply_threshold=auto,
        suggest_threshold=suggest,
    )
