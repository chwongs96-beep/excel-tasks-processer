"""Canonical schema helpers backed by YAML configuration."""

from __future__ import annotations

from reporting.config_loader import SchemaConfig, load_app_config


def get_schema() -> SchemaConfig:
    """Return the canonical schema from configuration."""
    return load_app_config().schema


def canonical_fields() -> tuple[str, ...]:
    return get_schema().canonical_fields


def required_fields() -> tuple[str, ...]:
    return get_schema().required_fields


def column_aliases() -> dict[str, tuple[str, ...]]:
    return get_schema().column_aliases
