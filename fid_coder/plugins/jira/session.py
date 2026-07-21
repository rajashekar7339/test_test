"""Single entrypoint for interactive Jira login.

Every caller that needs to open a browser and capture a session cookie
(the ``jira_login`` tool, ``/jira login``, and the automatic missing-cookie
/ 403 retries in ``read_jira_issue``) goes through
:func:`perform_jira_login` so there is exactly one place that resolves the
URL, talks to Playwright, persists the cookie, and emits user-facing status
messages.
"""

from __future__ import annotations

from typing import Optional

from .auth import JIRA_SECTION, save_section
from .config import JiraCredentials, get_jira_credentials
from .login import ensure_jira_cookie, resolve_jira_url


class JiraLoginError(Exception):
    """Raised when interactive Jira login cannot proceed or fails."""


def perform_jira_login(*, url: Optional[str] = None, force: bool = True) -> str:
    """Open a browser, capture a Jira session cookie, and persist it.

    Args:
        url: Explicit Jira base URL. Falls back to the resolved config URL
            (env / ``authentication.json`` / ``fid.cfg``) when omitted.
        force: Re-capture even if a cookie is already stored. Defaults to
            ``True`` since every current caller wants a fresh session.

    Returns:
        The resolved base URL that was logged into.

    Raises:
        JiraLoginError: URL could not be resolved, or the browser capture
            failed for any reason.
    """
    from fid_coder.messaging import emit_info

    resolved_url = resolve_jira_url(url)
    if not resolved_url:
        raise JiraLoginError(
            "Jira URL is not set. Provide one, e.g. `/jira login "
            "https://jira.<company>.com`."
        )

    # Persist the URL before opening the browser so a cancelled login still
    # remembers the host for the next attempt.
    save_section(JIRA_SECTION, {"url": resolved_url})

    emit_info(f"Opening browser for Jira login → {resolved_url}")
    try:
        ensure_jira_cookie(base_url=resolved_url, force=force)
    except Exception as e:
        raise JiraLoginError(f"Browser login failed: {e}") from e

    return resolved_url


def refresh_credentials_after_login() -> JiraCredentials:
    """Re-resolve credentials from the auth file after a successful login."""
    return get_jira_credentials()
