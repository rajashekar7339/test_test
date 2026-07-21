"""Interactive Jira browser login → capture session cookie into authentication.json."""

from __future__ import annotations

import concurrent.futures
import time
from typing import Optional
from urllib.parse import urlparse

from .auth import JIRA_SECTION, get_section, save_section
from .config import get_jira_url, normalize_jira_url

# Cookie names that indicate a logged-in Jira session (Server/DC + Cloud-ish).
_SESSION_COOKIE_HINTS = (
    "JSESSIONID",
    "seraph.rememberme.cookie",
    "tenant.session.token",
    "cloud.session.token",
    "atlassian.account.session",
)

# How long to wait for SSO before giving up (user stays in the browser).
_LOGIN_WAIT_TIMEOUT_S = 5 * 60
_LOGIN_POLL_INTERVAL_S = 1.0


def resolve_jira_url(explicit: Optional[str] = None) -> Optional[str]:
    """Return a Jira base URL from arg, auth file, env, or config."""
    if explicit and explicit.strip():
        return normalize_jira_url(explicit)

    url = get_jira_url()
    return normalize_jira_url(url) if url else None


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


def _domain_matches(host: str, domain: str) -> bool:
    """Standard cookie scoping: exact host, or ``host`` under ``domain``."""
    domain = domain.lstrip(".")
    return host == domain or host.endswith(f".{domain}")


def _cookies_for_host(cookies: list[dict], host: str) -> list[dict]:
    """Prefer cookies scoped to ``host``; fall back to the full jar."""
    if not host:
        return list(cookies)
    host_cookies = [
        c for c in cookies if _domain_matches(host, str(c.get("domain", "")))
    ]
    return host_cookies or list(cookies)


def _wait_for_session_cookie(context) -> None:
    """Poll the browser cookie jar until a Jira session cookie appears.

    Accepts a session cookie anywhere in the jar (SSO may set it on a
    different domain than base_url). Returns on timeout too — the caller
    re-reads the jar and reports a clear error if login never completed.
    """
    deadline = time.monotonic() + _LOGIN_WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        if _looks_logged_in(context.cookies()):
            return
        time.sleep(_LOGIN_POLL_INTERVAL_S)


def _running_in_asyncio_loop() -> bool:
    try:
        import asyncio

        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _capture_jira_cookie_sync(base_url: str) -> tuple[str, str]:
    """Playwright Sync API body — must not run on the main asyncio loop thread.

    Returns ``(cookie_header, final_origin)``.
    """
    from playwright.sync_api import sync_playwright

    from fid_coder.messaging import emit_info, emit_success, emit_warning

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(
            f"Invalid JIRA_URL '{base_url}'. Expected https://jira.<company>.com"
        )

    emit_info(
        "Log in with SSO in the browser window — cookies are captured "
        "automatically when the session is ready (no Enter needed)."
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
            except Exception as e:
                emit_warning(f"Initial navigation warning (you can still log in): {e}")

            # Wait until SSO finishes and a session cookie shows up — no
            # manual Enter needed.
            _wait_for_session_cookie(context)

            # Prefer the origin we actually landed on (often https after SSO
            # redirect) and scope cookies to that host.
            final_parsed = urlparse(page.url or base_url)
            host = final_parsed.hostname or parsed.hostname or ""
            host_cookies = _cookies_for_host(context.cookies(), host)
        finally:
            browser.close()

    if final_parsed.scheme and final_parsed.netloc:
        origin = normalize_jira_url(f"{final_parsed.scheme}://{final_parsed.netloc}")
    else:
        origin = normalize_jira_url(base_url)

    header = _cookies_to_header(host_cookies)
    if not header:
        raise RuntimeError(
            "No cookies captured. Finish SSO login in the browser window "
            f"within {_LOGIN_WAIT_TIMEOUT_S // 60} minutes."
        )

    if not _looks_logged_in(host_cookies):
        raise RuntimeError(
            "Timed out waiting for a Jira session cookie "
            "(JSESSIONID / cloud.session.token). Finish SSO login in the "
            "browser and try again."
        )

    emit_success("Captured Jira session cookies.")
    return header, origin


def capture_jira_cookie_via_browser(base_url: str) -> tuple[str, str]:
    """Open headed Chromium on ``base_url``, wait for login.

    Returns ``(cookie_header, final_origin)``.

    Fid's TUI runs inside an asyncio loop; Playwright's Sync API refuses to
    start there, so we hop to a worker thread (same pattern as ``/btw`` and
    theme pickers) when a loop is already running.
    """
    if _running_in_asyncio_loop():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_capture_jira_cookie_sync, base_url).result()
    return _capture_jira_cookie_sync(base_url)


def ensure_jira_cookie(*, base_url: Optional[str] = None, force: bool = False) -> str:
    """Return a Jira cookie, launching browser login when missing (or ``force``).

    Persists the cookie (and url) under the ``jira`` section of
    ``authentication.json``.
    """
    section = get_section(JIRA_SECTION)
    existing = section.get("cookie")
    if existing and not force:
        return existing

    url = resolve_jira_url(base_url) or (
        normalize_jira_url(section["url"]) if section.get("url") else None
    )
    if not url:
        raise RuntimeError(
            "JIRA_URL is not set. Run `/jira login https://jira.<company>.com`."
        )

    cookie, origin = capture_jira_cookie_via_browser(url)
    save_section(JIRA_SECTION, {"url": origin, "cookie": cookie})
    return cookie
