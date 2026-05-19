"""Logging configuration."""

from __future__ import annotations

import logging
import sys

from app.core import config

_LOGGER_NAME = "report_desktop"
_configured = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    global _configured  # noqa: PLW0603
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    config.ensure_dirs()
    file_handler = logging.FileHandler(config.LOGS_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
