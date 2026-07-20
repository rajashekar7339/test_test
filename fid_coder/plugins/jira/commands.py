"""``/jira`` slash command — configure auth + browser login (no secret echo)."""

from __future__ import annotations

import os
from typing import Any, Optional

from .auth import get_auth_file_path, get_section, save_auth_file
from .config import JiraConfigError, get_jira_credentials

COMMAND_NAME = "jira"

_USAGE = """\
/jira — Jira auth helpers

  /jira login [url]         Open jira.<company>.com, capture session cookie,
                            save to ~/.fid_coder/authentication.json
  /jira status              Show whether URL/cookie are configured (no secrets)
  /jira set url <url>       Save jira.url in authentication.json
  /jira set cookie <value>  Manually save jira.cookie (Cookie header paste)
  /jira clear cookie        Remove jira.cookie
  /jira clear url           Remove jira.url
  /jira help                Show this help

If no cookie is stored, `read_jira_issue` (and `/jira login`) open a browser
so you can SSO-login; cookies are saved under the `jira` section of
authentication.json (~7 day sessions — re-run `/jira login` on 401).
"""


def custom_command_help() -> list[tuple[str, str]]:
    return [
        (
            "/jira login [url]",
            "Open Jira in a browser, capture cookie → authentication.json",
        ),
        ("/jira status", "Show Jira auth status (no secrets)"),
        ("/jira set cookie <value>", "Manually save cookie to authentication.json"),
        ("/jira set url <url>", "Save Jira URL to authentication.json"),
    ]


def _emit_status() -> None:
    from fid_coder.messaging import emit_info, emit_warning

    path = get_auth_file_path()
    section = get_section("jira")
    has_url = bool(section.get("url") or os.environ.get("JIRA_URL"))
    has_cookie = bool(section.get("cookie") or os.environ.get("JIRA_COOKIE"))

    emit_info(f"Auth file: {path}")
    emit_info(f"  jira.url:    {'set' if has_url else 'missing'}")
    emit_info(f"  jira.cookie: {'set' if has_cookie else 'missing'}")

    try:
        creds = get_jira_credentials(interactive_login=False)
        mode = (
            "cookie"
            if creds.cookie
            else (
                "personal_token"
                if creds.personal_token
                else ("basic" if creds.email and creds.api_token else "bearer_token")
            )
        )
        emit_info(f"  Resolved:    ok ({mode}) → {creds.base_url}")
    except JiraConfigError as e:
        emit_warning(f"  Resolved:    incomplete — {e}")


def _handle_login(args: list[str]) -> bool:
    from fid_coder.messaging import emit_error, emit_success

    from .login import ensure_jira_cookie, resolve_jira_url

    url_arg = args[0].strip() if args else None
    url = resolve_jira_url(url_arg)
    if not url:
        emit_error("Need a Jira URL. Usage: /jira login https://jira.<company>.com")
        return True

    # Persist URL first so a cancelled login still remembers the host.
    save_auth_file({"JIRA_URL": url})

    try:
        ensure_jira_cookie(base_url=url, force=True)
    except Exception as e:
        emit_error(f"Jira login failed: {e}")
        return True

    emit_success(
        f"Saved jira session to {get_auth_file_path()} (cookie value not echoed)"
    )
    return True


def _handle_set(args: list[str]) -> bool:
    from fid_coder.messaging import emit_error, emit_success

    if len(args) < 2:
        emit_error("Usage: /jira set url <url> | /jira set cookie <value>")
        return True

    what = args[0].lower()
    value = " ".join(args[1:]).strip()
    if not value:
        emit_error(f"Usage: /jira set {what} <value>")
        return True

    if what == "url":
        from .config import normalize_jira_url

        path = save_auth_file({"JIRA_URL": normalize_jira_url(value)})
        emit_success(f"Saved jira.url to {path}")
        return True
    if what == "cookie":
        path = save_auth_file({"JIRA_COOKIE": value})
        emit_success(f"Saved jira.cookie to {path} (value not echoed)")
        return True

    emit_error(f"Unknown key '{what}'. Use: url, cookie")
    return True


def _handle_clear(args: list[str]) -> bool:
    from fid_coder.messaging import emit_error, emit_success

    if not args:
        emit_error("Usage: /jira clear cookie | /jira clear url")
        return True

    what = args[0].lower()
    key = {"cookie": "JIRA_COOKIE", "url": "JIRA_URL"}.get(what)
    if not key:
        emit_error(f"Unknown key '{what}'. Use: cookie, url")
        return True

    path = save_auth_file({}, clear=[key])
    emit_success(f"Cleared {what} from {path}")
    return True


def handle_custom_command(command: str, name: str) -> Optional[Any]:
    if name != COMMAND_NAME:
        return None

    from fid_coder.messaging import emit_info

    parts = command.strip().split()
    sub = parts[1].lower() if len(parts) > 1 else "status"

    if sub in {"help", "-h", "--help"}:
        emit_info(_USAGE)
        return True
    if sub == "status":
        _emit_status()
        return True
    if sub == "login":
        return _handle_login(parts[2:])
    if sub == "set":
        return _handle_set(parts[2:])
    if sub == "clear":
        return _handle_clear(parts[2:])

    emit_info(_USAGE)
    return True
