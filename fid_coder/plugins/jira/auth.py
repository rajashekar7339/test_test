"""Generic credentials store: ``~/.fid_coder/authentication.json``.

Shape (extensible per service)::

    {
      "jira": {
        "url": "https://jira.company.com",
        "cookie": "JSESSIONID=...; ..."
      }
    }

File mode is ``0o600`` so only the owner can read credentials.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from fid_coder.config import CONFIG_DIR

logger = logging.getLogger(__name__)

AUTH_FILENAME = "authentication.json"
AUTH_FILE_MODE = 0o600
JIRA_SECTION = "jira"


def get_auth_file_path() -> str:
    """Absolute path to the shared authentication file."""
    return os.path.join(CONFIG_DIR, AUTH_FILENAME)


def _normalize_loaded(data: Any) -> dict[str, Any]:
    """Keep only service sections (dict values with string fields)."""
    if not isinstance(data, dict):
        return {}

    out: dict[str, Any] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        out[key] = {
            str(k): str(v).strip()
            for k, v in value.items()
            if isinstance(k, str) and isinstance(v, str) and str(v).strip()
        }
    return out


def _flat_key_to_section_key(flat: str) -> str:
    """``JIRA_COOKIE`` → ``cookie``, ``JIRA_URL`` → ``url``."""
    if flat.upper().startswith("JIRA_"):
        return flat[5:].lower()
    return flat.lower()


def load_auth_file() -> dict[str, Any]:
    """Load ``authentication.json``. Missing/invalid file → empty dict."""
    path = get_auth_file_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return _normalize_loaded(json.load(f))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to read %s: %s", path, e)
        return {}


def _write_raw(data: dict[str, Any]) -> str:
    path = get_auth_file_path()
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp_path = f"{path}.tmp"
    # Create the temp file 0o600 from the start so credentials are never
    # world-readable, even briefly.
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, AUTH_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, path)
    try:
        os.chmod(path, AUTH_FILE_MODE)
    except OSError:
        pass
    return path


def get_section(service: str) -> dict[str, str]:
    """Return one service section (e.g. ``jira``) as string key/values."""
    section = load_auth_file().get(service) or {}
    if not isinstance(section, dict):
        return {}
    return {
        str(k): str(v)
        for k, v in section.items()
        if isinstance(k, str) and isinstance(v, str) and v.strip()
    }


def save_section(
    service: str,
    updates: dict[str, str],
    *,
    clear: Optional[list[str]] = None,
) -> str:
    """Merge ``updates`` into ``service`` section and persist the file."""
    data = load_auth_file()
    section = dict(data.get(service) or {})
    if not isinstance(section, dict):
        section = {}

    for key in clear or []:
        section.pop(key, None)
        section.pop(key.upper(), None)

    for key, value in updates.items():
        if not key or not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            section[key] = stripped

    if section:
        data[service] = section
    else:
        data.pop(service, None)

    return _write_raw(data)


def get_auth_value(name: str) -> Optional[str]:
    """Resolve a flat env-style name (``JIRA_COOKIE``) from the jira section."""
    if not name.upper().startswith("JIRA_"):
        return None
    section_key = _flat_key_to_section_key(name)
    return get_section(JIRA_SECTION).get(section_key)
