"""Credential resolution for the Jira plugin.

Auth sources (first match wins per key):
1. Environment variables
2. ``~/.fid_coder/authentication.json`` → ``jira`` section
3. Fid Coder persistent config (``/set`` / ``get_value``)

Supported auth modes:
- Browser session cookie → ``Cookie`` header (``jira.cookie`` / ``JIRA_COOKIE``)
- Data Center PAT → ``Authorization: Bearer`` (``JIRA_PERSONAL_TOKEN``)
- Cloud API token → HTTP Basic (``JIRA_EMAIL`` + ``JIRA_API_TOKEN``)
- Bare token without email → treated as Bearer

When no cookie/token is present, callers (e.g. ``read_jira_issue``) open a
browser login against ``JIRA_URL`` and save the captured cookie into
``authentication.json``. This module only resolves credentials.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from fid_coder.config import get_value

from .auth import get_auth_value


def _resolve(*names: str) -> Optional[str]:
    """Return the first non-empty value: env → auth file → config."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    for name in names:
        value = get_auth_value(name)
        if value:
            return value
    for name in names:
        value = get_value(name)
        if value:
            return value
    return None


def normalize_jira_url(url: str) -> str:
    """Strip trailing slash; upgrade bare ``http://`` Jira hosts to ``https://``.

    Many corporate instances permanently redirect http→https (HTTP 301). Using
    https up front avoids redirect / cookie edge cases on the REST client.
    """
    cleaned = url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme == "http" and parsed.netloc:
        cleaned = cleaned.replace("http://", "https://", 1)
    return cleaned


def get_jira_url() -> Optional[str]:
    """Resolved Jira base URL, or ``None``.

    Upgrades ``http://`` → ``https://`` so stored corporate URLs that 301
    redirect do not break REST calls.
    """
    url = _resolve("JIRA_URL")
    return normalize_jira_url(url) if url else None


@dataclass
class JiraCredentials:
    """Resolved Jira connection info, ready to build request headers."""

    base_url: str
    cookie: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    personal_token: Optional[str] = None

    @property
    def request_headers(self) -> dict[str, str]:
        """Auth-related headers for Jira REST calls."""
        if self.cookie:
            return {"Cookie": self.cookie}
        if self.personal_token:
            return {"Authorization": f"Bearer {self.personal_token}"}
        if self.email and self.api_token:
            raw = f"{self.email}:{self.api_token}".encode("utf-8")
            encoded = base64.b64encode(raw).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}
        if self.api_token:
            return {"Authorization": f"Bearer {self.api_token}"}
        return {}


class JiraConfigError(Exception):
    """Raised when Jira credentials are missing or incomplete."""


def get_jira_credentials() -> JiraCredentials:
    """Resolve Jira credentials, raising ``JiraConfigError`` if incomplete.

    Pure resolution — never opens a browser or has other side effects.
    Callers that need an interactive login (missing/expired cookie) should
    go through ``session.perform_jira_login`` and re-resolve afterwards.
    """
    base_url = get_jira_url()
    if not base_url:
        raise JiraConfigError(
            "JIRA_URL is not set. Run `/jira login https://jira.<company>.com` "
            "(saved under jira.url in ~/.fid_coder/authentication.json)."
        )

    cookie = _resolve("JIRA_COOKIE")
    email = _resolve("JIRA_EMAIL", "JIRA_USERNAME")
    api_token = _resolve("JIRA_API_TOKEN", "JIRA_TOKEN")
    personal_token = _resolve("JIRA_PERSONAL_TOKEN")

    if not (cookie or personal_token or api_token):
        raise JiraConfigError(
            "No Jira credentials in ~/.fid_coder/authentication.json "
            "(no jira.cookie / token). Callers should open a browser login."
        )

    return JiraCredentials(
        base_url=base_url,
        cookie=cookie,
        email=email,
        api_token=api_token,
        personal_token=personal_token,
    )
