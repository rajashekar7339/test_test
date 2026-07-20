"""Plugin-local config for the emoji_filter plugin.

Filter is always on — no user toggle.
"""

from __future__ import annotations


def is_enabled() -> bool:
    """Emoji filtering is always enabled."""
    return True
