"""Jira agent tools: fetch/search issues, and interactive login."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .client import JiraFetchError, fetch_issue, search_issues
from .config import JiraConfigError, JiraCredentials, get_jira_credentials
from .session import JiraLoginError, perform_jira_login, refresh_credentials_after_login

# A tool call against Jira: takes resolved credentials, returns (payload, error).
JiraCall = Callable[
    [JiraCredentials],
    Awaitable[tuple[Optional[dict[str, Any]], Optional[JiraFetchError]]],
]


class JiraIssueOutput(BaseModel):
    """Normalized fields for a single Jira issue."""

    key: str
    url: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    error: Optional[str] = None


class JiraSearchOutput(BaseModel):
    """Normalized JQL search result."""

    jql: str
    total: int = 0
    start_at: int = 0
    max_results: int = 0
    issues: list[JiraIssueOutput] = Field(default_factory=list)
    error: Optional[str] = None


class JiraLoginOutput(BaseModel):
    """Result of opening a browser to capture a Jira session cookie."""

    ok: bool
    url: Optional[str] = None
    message: str


def _person_name(field: Optional[dict[str, Any]]) -> Optional[str]:
    if not field:
        return None
    return field.get("displayName") or field.get("name") or field.get("emailAddress")


def _normalize_issue(
    base_url: str, issue_key: str, payload: dict[str, Any]
) -> JiraIssueOutput:
    fields = payload.get("fields", {}) or {}
    return JiraIssueOutput(
        key=payload.get("key", issue_key),
        url=f"{base_url}/browse/{payload.get('key', issue_key)}",
        summary=fields.get("summary"),
        status=(fields.get("status") or {}).get("name"),
        issue_type=(fields.get("issuetype") or {}).get("name"),
        priority=(fields.get("priority") or {}).get("name"),
        assignee=_person_name(fields.get("assignee")),
        reporter=_person_name(fields.get("reporter")),
        labels=fields.get("labels") or [],
        description=fields.get("description"),
        created=fields.get("created"),
        updated=fields.get("updated"),
    )


async def _ensure_credentials() -> tuple[Optional[JiraCredentials], Optional[str]]:
    """Resolve credentials; open a browser login once if none are stored."""
    try:
        return get_jira_credentials(), None
    except JiraConfigError:
        try:
            await asyncio.to_thread(perform_jira_login, force=True)
            return refresh_credentials_after_login(), None
        except (JiraLoginError, JiraConfigError) as e:
            return None, (
                f"No Jira credentials configured, and automatic login failed: {e}"
            )


async def _call_jira(
    call: JiraCall,
) -> tuple[Optional[JiraCredentials], Optional[dict[str, Any]], Optional[str]]:
    """Run one authenticated Jira call, re-logging-in once on a cookie 403.

    Handles the full auth lifecycle shared by every read tool: resolve
    credentials (opening a browser login when none are stored), execute
    ``call``, and — if a cookie-based session is rejected with 403 — force
    one interactive re-login and retry.

    Returns ``(credentials, payload, error_message)``; exactly one of
    ``payload`` / ``error_message`` is set.
    """
    credentials, cred_error = await _ensure_credentials()
    if credentials is None:
        return None, None, cred_error or "Missing credentials."

    payload, error = await call(credentials)
    if error is None:
        return credentials, payload, None

    if error.status_code != 403 or not credentials.cookie:
        return credentials, None, error.message

    try:
        await asyncio.to_thread(
            perform_jira_login, url=credentials.base_url, force=True
        )
        credentials = refresh_credentials_after_login()
    except (JiraLoginError, JiraConfigError) as e:
        return (
            credentials,
            None,
            (
                f"{error.message} Automatic re-login failed: {e}. "
                "Ask me to log in again (I'll open the browser)."
            ),
        )

    payload, error = await call(credentials)
    if error is not None:
        return credentials, None, error.message
    return credentials, payload, None


def register_jira_login(agent):
    """Register the ``jira_login`` tool on ``agent``."""

    @agent.tool
    async def jira_login(context: RunContext) -> JiraLoginOutput:
        """Open a browser so the user can SSO-login to Jira.

        Uses the configured Jira base URL from config / authentication.json
        (no URL argument needed). Saves the session cookie automatically.
        Call this when the user asks to log in to Jira, or when credentials
        are missing / expired.
        """
        try:
            # Playwright and the SSO wait loop block for minutes; run on a
            # worker thread so the agent turn (spinner, streaming,
            # cancellation) doesn't freeze while the browser is open.
            url = await asyncio.to_thread(perform_jira_login, force=True)
        except JiraLoginError as e:
            return JiraLoginOutput(ok=False, message=str(e))

        return JiraLoginOutput(
            ok=True,
            url=url,
            message=(
                f"Logged in to {url}. Session cookie saved to "
                "~/.fid_coder/authentication.json."
            ),
        )


def register_read_jira_issue(agent):
    """Register the ``read_jira_issue`` tool on ``agent``."""

    @agent.tool
    async def read_jira_issue(
        context: RunContext, issue_key: str = ""
    ) -> JiraIssueOutput:
        """Fetch a Jira issue's details by key (e.g. ``PROJ-123``).

        Returns summary, status, type, priority, assignee, reporter, labels,
        description, and timestamps. Requires JIRA_URL; uses jira.cookie
        from `~/.fid_coder/authentication.json`, or JIRA_PERSONAL_TOKEN /
        JIRA_EMAIL+JIRA_API_TOKEN. If no cookie/token is stored, opens a
        browser login automatically (no user confirmation), then retries.
        On 403 with a cookie session, automatically re-logs in once and retries.
        """
        key = issue_key.strip()
        if not key:
            return JiraIssueOutput(
                key=issue_key, error="issue_key is required, e.g. 'PROJ-123'."
            )

        credentials, payload, error = await _call_jira(
            lambda creds: fetch_issue(creds, key)
        )
        if error or credentials is None:
            return JiraIssueOutput(key=key, error=error or "Missing credentials.")

        return _normalize_issue(credentials.base_url, key, payload or {})


def register_search_jira_issues(agent):
    """Register the ``search_jira_issues`` tool on ``agent``."""

    @agent.tool
    async def search_jira_issues(
        context: RunContext,
        jql: str = "",
        max_results: int = 50,
    ) -> JiraSearchOutput:
        """Search Jira with a JQL query string.

        You (the model) translate the user's natural-language request into JQL.
        Examples the user might ask, and JQL you might use:
        - tickets in epic PROJ-123 → `"Epic Link" = PROJ-123 OR parent = PROJ-123`
        - my open bugs → `assignee = currentUser() AND type = Bug AND resolution = Unresolved`
        - recent in project ABC → `project = ABC ORDER BY updated DESC`

        Returns matching issues (key, summary, status, type, …) plus total count.
        Caps ``max_results`` at 100. Auth/login behaves like ``read_jira_issue``.
        """
        query = (jql or "").strip()
        if not query:
            return JiraSearchOutput(
                jql=jql,
                error="jql is required. Translate the user's request into JQL.",
            )

        limit = max(1, min(int(max_results or 50), 100))

        credentials, payload, error = await _call_jira(
            lambda creds: search_issues(creds, query, max_results=limit)
        )
        if error or credentials is None:
            return JiraSearchOutput(jql=query, error=error or "Missing credentials.")

        data = payload or {}
        issues = [
            _normalize_issue(credentials.base_url, issue.get("key", ""), issue)
            for issue in (data.get("issues") or [])
            if isinstance(issue, dict)
        ]
        return JiraSearchOutput(
            jql=query,
            total=int(data.get("total") or len(issues)),
            start_at=int(data.get("startAt") or 0),
            max_results=int(data.get("maxResults") or limit),
            issues=issues,
        )
