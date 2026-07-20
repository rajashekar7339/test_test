"""Interactive Jira browser login → capture session cookie into authentication.json."""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from .auth import JIRA_SECTION, get_section, save_section

logger = logging.getLogger(__name__)

# Cookie names that indicate a logged-in Jira session (Server/DC + Cloud-ish).
_SESSION_COOKIE_HINTS = (
    "JSESSIONID",
    "seraph.rememberme.cookie",
    "tenant.session.token",
    "cloud.session.token",
    "atlassian.account.session",
)


def resolve_jira_url(explicit: Optional[str] = None) -> Optional[str]:
    """Return a Jira base URL from arg, auth file, env, or config."""
    if explicit and explicit.strip():
        return explicit.strip().rstrip("/")

    from .config import get_jira_url

    return get_jira_url()


def _cookies_to_header(cookies: list[dict]) -> str:
    """Format Playwright cookie dicts as a Cookie request header value."""
    parts = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if name and value is not None:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def _looks_logged_in(cookies: list[dict]) -> bool:
    names = {str(c.get("name", "")) for c in cookies}
    return any(hint in names for hint in _SESSION_COOKIE_HINTS)


def capture_jira_cookie_via_browser(base_url: str) -> str:
    """Open headed Chromium on ``base_url``, wait for login, return Cookie header.

    Blocks until the user presses Enter in the terminal after finishing SSO
    login in the browser window. Raises ``RuntimeError`` on failure.
    """
    from playwright.sync_api import sync_playwright

    from fid_coder.messaging import emit_info, emit_success, emit_warning

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(
            f"Invalid JIRA_URL '{base_url}'. Expected https://jira.<company>.com"
        )

    emit_info(f"Opening browser for Jira login: {base_url}")
    emit_info("Log in with SSO if prompted, then return here and press Enter.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            emit_warning(f"Initial navigation warning (you can still log in): {e}")

        try:
            from fid_coder.command_line.utils import safe_input

            safe_input("Press Enter after you have logged into Jira… ")
        except (EOFError, KeyboardInterrupt) as e:
            browser.close()
            raise RuntimeError("Jira login cancelled.") from e

        cookies = context.cookies()
        # Prefer cookies for the Jira host; fall back to all if filter is empty.
        host = parsed.hostname or ""
        host_cookies = [
            c for c in cookies if host and host in str(c.get("domain", "")).lstrip(".")
        ] or list(cookies)

        browser.close()

    header = _cookies_to_header(host_cookies)
    if not header:
        raise RuntimeError(
            "No cookies captured. Make sure you finished login in the browser "
            "window before pressing Enter."
        )

    if not _looks_logged_in(host_cookies):
        emit_warning(
            "No obvious Jira session cookie (JSESSIONID / cloud.session.token) "
            "found — saving captured cookies anyway."
        )
    else:
        emit_success("Captured Jira session cookies.")

    return header


def ensure_jira_cookie(*, base_url: Optional[str] = None, force: bool = False) -> str:
    """Return a Jira cookie, launching browser login when missing (or ``force``).

    Persists the cookie (and url) under the ``jira`` section of
    ``authentication.json``.
    """
    section = get_section(JIRA_SECTION)
    existing = section.get("cookie")
    if existing and not force:
        return existing

    url = resolve_jira_url(base_url) or section.get("url")
    if not url:
        raise RuntimeError(
            "JIRA_URL is not set. Run `/jira set url https://jira.<company>.com` "
            "or `/jira login https://jira.<company>.com`."
        )

    cookie = capture_jira_cookie_via_browser(url)
    save_section(JIRA_SECTION, {"url": url, "cookie": cookie})
    return cookie
