"""Credential resolution for the Jira plugin.

Supports both Jira Cloud (email + API token, HTTP Basic) and Jira Server /
Data Center (Personal Access Token, Bearer). Values are read from the
environment first, then from Fid Coder's persistent config file, so users
can either ``export JIRA_URL=...`` or ``/set JIRA_URL=...`` (which persists
via ``set_config_value``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from fid_coder.config import get_value


def _resolve(*names: str) -> Optional[str]:
    """Return the first non-empty value for any of ``names``, env then config."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    for name in names:
        value = get_value(name)
        if value:
            return value
    return None


@dataclass
class JiraCredentials:
    """Resolved Jira connection info, ready to build request auth."""

    base_url: str
    email: Optional[str] = None
    api_token: Optional[str] = None
    personal_token: Optional[str] = None

    @property
    def auth_header(self) -> dict[str, str]:
        """Build the ``Authorization`` header for this credential set."""
        if self.personal_token:
            return {"Authorization": f"Bearer {self.personal_token}"}
        if self.email and self.api_token:
            import base64

            raw = f"{self.email}:{self.api_token}".encode("utf-8")
            encoded = base64.b64encode(raw).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}
        if self.api_token:
            # Token present with no email: treat as a bearer/PAT-style token
            # (covers Data Center users who set JIRA_TOKEN for a PAT).
            return {"Authorization": f"Bearer {self.api_token}"}
        return {}


class JiraConfigError(Exception):
    """Raised when Jira credentials are missing or incomplete."""


def get_jira_credentials() -> JiraCredentials:
    """Resolve Jira credentials, raising ``JiraConfigError`` if incomplete.

    Recognized variables:
        JIRA_URL              - base URL, e.g. https://jira.company.com
        JIRA_EMAIL / JIRA_USERNAME - Cloud basic-auth user
        JIRA_API_TOKEN / JIRA_TOKEN - Cloud API token (or a bare token)
        JIRA_PERSONAL_TOKEN    - explicit Data Center PAT (Bearer)
    """
    base_url = _resolve("JIRA_URL")
    if not base_url:
        raise JiraConfigError(
            "JIRA_URL is not set. Set it to your Jira base URL, e.g. "
            "https://jira.<company>.com (via `export JIRA_URL=...` or "
            "`/set JIRA_URL=...`)."
        )

    email = _resolve("JIRA_EMAIL", "JIRA_USERNAME")
    api_token = _resolve("JIRA_API_TOKEN", "JIRA_TOKEN")
    personal_token = _resolve("JIRA_PERSONAL_TOKEN")

    if not (personal_token or api_token):
        raise JiraConfigError(
            "No Jira credentials found. Set either JIRA_PERSONAL_TOKEN "
            "(Data Center Personal Access Token) or JIRA_EMAIL + "
            "JIRA_API_TOKEN (Cloud API token from "
            "https://id.atlassian.com/manage-profile/security/api-tokens)."
        )

    return JiraCredentials(
        base_url=base_url.rstrip("/"),
        email=email,
        api_token=api_token,
        personal_token=personal_token,
    )
