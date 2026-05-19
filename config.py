"""
Backward-compatible shim — prefer ``import app_config``.

The YAML settings live in the ``config/`` directory; this module is Python settings only.
"""

from app_config import *  # noqa: F403
