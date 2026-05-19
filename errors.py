"""Backward-compatible shim — use reporting.models instead."""

from reporting.models import BLOCKING_CODES, LoadResult, ValidationIssue

__all__ = ["ValidationIssue", "LoadResult", "BLOCKING_CODES"]
