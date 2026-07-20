"""Interactive picker for adding GitHub Copilot models.

Same entrypoint shape as code_puppy (``interactive_model_picker()``), but
Copilot-only. Async so it can run under fid-coder's async command loop
(same pattern as ``/model``).
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from fid_coder.messaging import emit_error, emit_info, emit_warning
from fid_coder.tools.common import arrow_select_async

from .config import COPILOT_AUTH_CONFIG, DEFAULT_COPILOT_MODELS
from .utils import (
    add_models_to_config,
    fetch_copilot_models,
    get_token_for_host,
    get_valid_session_token,
    load_copilot_models,
    load_device_tokens,
)

_PREFIX = COPILOT_AUTH_CONFIG["prefix"]


def _registered_ids() -> Set[str]:
    ids: Set[str] = set()
    for key, cfg in load_copilot_models().items():
        if cfg.get("oauth_source") != "copilot-auth-plugin":
            continue
        ids.add(str(cfg.get("name") or key.removeprefix(_PREFIX)))
    return ids


def _session() -> Optional[Tuple[str, str]]:
    tokens = load_device_tokens()
    if not tokens:
        emit_warning(
            "GitHub Copilot is not authenticated.\n"
            "   Run /copilot-login first, then /add_model."
        )
        return None
    preferred = get_token_for_host("github.com") or tokens[0]
    session = get_valid_session_token(preferred.oauth_token, preferred.host)
    if not session:
        emit_error(
            f"Could not get a Copilot session for {preferred.host}.\n"
            f"   Run /copilot-login {preferred.host} and try again."
        )
        return None
    return preferred.host, session


def _fetch_models(session: str, host: str) -> List[str]:
    models = fetch_copilot_models(session, host) or list(DEFAULT_COPILOT_MODELS)
    seen: Set[str] = set()
    out: List[str] = []
    for mid in models:
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


async def interactive_model_picker() -> bool:
    """Browse Copilot models and register the selected one.

    Returns:
        True if a model was added, False otherwise.
    """
    auth = _session()
    if auth is None:
        return False
    host, session = auth

    emit_info("Fetching available Copilot models…")
    models = _fetch_models(session, host)
    if not models:
        emit_warning("No Copilot models available.")
        return False

    registered = _registered_ids()
    choices = [f"{mid}  ✓ registered" if mid in registered else mid for mid in models]

    try:
        selected = await arrow_select_async("Add Copilot model", choices)
    except (KeyboardInterrupt, EOFError):
        return False

    bare = selected.split("  ✓", 1)[0].strip()
    if bare in registered:
        emit_info(f"Already registered: {_PREFIX}{bare}\n   Use /model to select it.")
        return False

    if add_models_to_config([bare], host):
        emit_info(f"Added {_PREFIX}{bare} — use /model to switch.")
        return True

    emit_error("Failed to save Copilot model.")
    return False
