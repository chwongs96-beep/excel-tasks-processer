"""Append-only operation log for accounting audit trail."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core import config


def _log_path() -> Path:
    config.ensure_dirs()
    return config.LOGS_DIR / "operations.jsonl"


def log_operation(event: str, **fields: Any) -> None:
    """Record one user-facing operation (import, merge, report, reconcile)."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    path = _log_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str))
        handle.write("\n")
