"""Interactive Jira browser login → capture session cookie into authentication.json.

A session is considered *good* only when ``GET /rest/api/2/myself`` returns
HTTP 200 with the cookie — not merely because a ``JSESSIONID`` exists
(Jira often sets an anonymous one before SSO finishes).
"""

from __future__ import annotations

import concurrent.futures
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from .auth import JIRA_SECTION, get_section, save_section
from .config import get_jira_url, normalize_jira_url

# Path fragments that mean the user is still on a login / SSO interstitial.
_LOGIN_PATH_HINTS = (
    "/login",
    "login.jsp",
    "samlsso",
    "/sso/",
    "/oauth",
    "/identity",
    "authgateway",
    "adfs",
)

# How long to wait for SSO before giving up (user stays in the browser).
_LOGIN_WAIT_TIMEOUT_S = 10 * 60
_LOGIN_POLL_INTERVAL_S = 1.5
_PROBE_TIMEOUT_S = 10.0


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


def _host_is_jira(page_host: str, jira_host: str) -> bool:
    if not page_host or not jira_host:
        return False
    return page_host == jira_host or page_host.endswith(f".{jira_host}")


def _url_past_login(url: str, jira_host: str) -> bool:
    """True when the browser is back on Jira (not the IdP / login page)."""
    parsed = urlparse(url or "")
    host = parsed.hostname or ""
    if not _host_is_jira(host, jira_host):
        return False
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    haystack = f"{path}?{query}"
    return not any(hint in haystack for hint in _LOGIN_PATH_HINTS)


def probe_session(base_url: str, cookie_header: str) -> tuple[bool, Optional[str]]:
    """Return ``(ok, display_name)`` by calling Jira's ``/myself`` endpoint.

    A *good* session is HTTP 200 with a JSON body identifying the user.
    401/403/redirect-to-login → bad (keep waiting / re-login).
    """
    if not base_url or not cookie_header.strip():
        return False, None

    url = f"{normalize_jira_url(base_url)}/rest/api/2/myself"
    headers = {
        "Accept": "application/json",
        "Cookie": cookie_header,
    }
    try:
        with httpx.Client(timeout=_PROBE_TIMEOUT_S, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
    except httpx.HTTPError:
        return False, None

    if response.status_code != 200:
        return False, None

    # Redirects to HTML login pages sometimes still land as 200 text/html.
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        return False, None

    try:
        payload = response.json()
    except ValueError:
        return False, None

    if not isinstance(payload, dict):
        return False, None

    # Authenticated users always have at least one of these; anonymous
    # responses (when allowed) typically lack them or look empty.
    name = (
        payload.get("displayName")
        or payload.get("name")
        or payload.get("accountId")
        or payload.get("key")
    )
    if not name:
        return False, None
    return True, str(name)


def _wait_for_good_session(
    context, page, base_url: str, jira_host: str
) -> tuple[str, str]:
    """Poll until cookies prove good via ``/myself``, then return them.

    Returns ``(cookie_header, origin)``. Raises ``RuntimeError`` on timeout.
    """
    from fid_coder.messaging import emit_info

    deadline = time.monotonic() + _LOGIN_WAIT_TIMEOUT_S
    last_status_at = 0.0
    last_probe_status: Optional[int] = None  # for status messages only

    emit_info(
        f"Waiting up to {_LOGIN_WAIT_TIMEOUT_S // 60} minutes for SSO — "
        "finish login in the browser. Session is accepted only after "
        "GET /rest/api/2/myself succeeds (bad/anonymous cookies are ignored)."
    )

    while time.monotonic() < deadline:
        try:
            current_url = page.url or ""
        except Exception:
            current_url = ""

        past_login = _url_past_login(current_url, jira_host)
        if past_login:
            final_parsed = urlparse(current_url or base_url)
            host = final_parsed.hostname or jira_host
            host_cookies = _cookies_for_host(context.cookies(), host)
            cookie_header = _cookies_to_header(host_cookies)

            if cookie_header:
                ok, display_name = probe_session(base_url, cookie_header)
                if ok:
                    if final_parsed.scheme and final_parsed.netloc:
                        origin = normalize_jira_url(
                            f"{final_parsed.scheme}://{final_parsed.netloc}"
                        )
                    else:
                        origin = normalize_jira_url(base_url)
                    emit_info(
                        "Good session confirmed via /myself"
                        + (f" as {display_name}" if display_name else "")
                        + " — closing browser."
                    )
                    return cookie_header, origin
                last_probe_status = 401  # treated as not-yet-good

        now = time.monotonic()
        if now - last_status_at >= 15.0:
            last_status_at = now
            remaining = int(deadline - now)
            if past_login:
                emit_info(
                    f"On Jira host — cookie present but /myself not OK yet "
                    f"(still a bad/anonymous session). Keep finishing SSO "
                    f"({remaining}s left)…"
                )
            else:
                host = urlparse(current_url).hostname or "(loading)"
                emit_info(
                    f"Still on SSO/login ({host}) — complete MFA if prompted "
                    f"({remaining}s left)…"
                )
            _ = last_probe_status  # reserved for richer status later

        time.sleep(_LOGIN_POLL_INTERVAL_S)

    raise RuntimeError(
        "Timed out waiting for a *good* Jira session "
        "(GET /rest/api/2/myself never returned 200). Finish SSO/MFA in the "
        "browser and try `/jira login` again."
    )


def _running_in_asyncio_loop() -> bool:
    try:
        import asyncio

        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def _capture_jira_cookie_sync(base_url: str) -> tuple[str, str]:
    """Playwright Sync API body — must not run on the main asyncio loop thread.

    Returns ``(cookie_header, final_origin)`` only after ``/myself`` succeeds.
    """
    from playwright.sync_api import sync_playwright

    from fid_coder.messaging import emit_info, emit_success, emit_warning

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(
            f"Invalid JIRA_URL '{base_url}'. Expected https://jira.<company>.com"
        )
    jira_host = parsed.hostname or ""
    base_url = normalize_jira_url(base_url)

    emit_info(f"Opening browser for Jira login: {base_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(0)
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=120_000)
            except Exception as e:
                emit_warning(f"Initial navigation warning (you can still log in): {e}")

            cookie_header, origin = _wait_for_good_session(
                context, page, base_url, jira_host
            )
        finally:
            browser.close()

    emit_success("Captured a verified Jira session cookie.")
    return cookie_header, origin


def capture_jira_cookie_via_browser(base_url: str) -> tuple[str, str]:
    """Open headed Chromium on ``base_url``, wait for a *good* session.

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
    """Return a *good* Jira cookie, launching browser login when needed.

    Reuses the saved cookie only if ``/myself`` still succeeds; otherwise
    opens the browser again. Persists under the ``jira`` section of
    ``authentication.json``.
    """
    section = get_section(JIRA_SECTION)
    url = resolve_jira_url(base_url) or (
        normalize_jira_url(section["url"]) if section.get("url") else None
    )
    if not url:
        raise RuntimeError(
            "JIRA_URL is not set. Run `/jira login https://jira.<company>.com`."
        )

    existing = section.get("cookie")
    if existing and not force:
        ok, _ = probe_session(url, existing)
        if ok:
            return existing
        # Stale / anonymous cookie — fall through to interactive login.

    cookie, origin = capture_jira_cookie_via_browser(url)
    save_section(JIRA_SECTION, {"url": origin, "cookie": cookie})
    return cookie
