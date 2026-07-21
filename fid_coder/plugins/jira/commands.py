"""``/jira`` slash command — manual browser login fallback.

The Jira agent normally logs in itself via the ``jira_login`` tool
(:mod:`fid_coder.plugins.jira.session`). This slash command exists for the
rare case where you want to (re)login outside of an agent turn, or supply an
explicit URL up front.
"""

from __future__ import annotations

from typing import Any, Optional

COMMAND_NAME = "jira"

_USAGE = """\
/jira — Jira browser login

  /jira login [url]  Open Jira in a browser, capture session cookie,
                      save to ~/.fid_coder/authentication.json
  /jira help          Show this help

Once logged in, the Jira agent uses the saved cookie automatically (and
re-logs in on its own if the session expires — ~7 day sessions).
"""


def custom_command_help() -> list[tuple[str, str]]:
    # NOTE: /help and the completion menu both prepend "/" themselves, so
    # entries here must be bare command names (no leading slash) or the
    # menu renders a double slash, e.g. "//jira login".
    return [
        (
            "jira login [url]",
            "Open Jira in a browser, capture cookie → authentication.json",
        ),
    ]


def _handle_login(args: list[str]) -> bool:
    from fid_coder.messaging import emit_error, emit_success

    from .session import JiraLoginError, perform_jira_login

    url_arg = args[0].strip() if args else None
    try:
        url = perform_jira_login(url=url_arg, force=True)
    except JiraLoginError as e:
        emit_error(str(e))
        return True

    emit_success(f"Logged in to {url}. Session cookie saved (value not echoed).")
    return True


def handle_custom_command(command: str, name: str) -> Optional[Any]:
    if name != COMMAND_NAME:
        return None

    from fid_coder.messaging import emit_info

    parts = command.strip().split()
    sub = parts[1].lower() if len(parts) > 1 else "login"

    if sub in {"help", "-h", "--help"}:
        emit_info(_USAGE)
        return True
    if sub == "login":
        return _handle_login(parts[2:])

    emit_info(_USAGE)
    return True
