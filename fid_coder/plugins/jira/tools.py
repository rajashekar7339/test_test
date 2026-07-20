"""``read_jira_issue`` tool - fetch and normalize a single Jira ticket."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel
from pydantic_ai import RunContext

from .client import fetch_issue
from .config import JiraConfigError, get_jira_credentials


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
    labels: list[str] = []
    description: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    error: Optional[str] = None


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


def register_read_jira_issue(agent):
    """Register the ``read_jira_issue`` tool on ``agent``."""

    @agent.tool
    async def read_jira_issue(
        context: RunContext, issue_key: str = ""
    ) -> JiraIssueOutput:
        """Fetch a Jira issue's details by key (e.g. ``PROJ-123``).

        Returns summary, status, type, priority, assignee, reporter, labels,
        description, and timestamps. Requires JIRA_URL; uses jira.cookie
        from `~/.fid_coder/authentication.json` (auto `/jira login` if
        missing), or JIRA_PERSONAL_TOKEN / JIRA_EMAIL+JIRA_API_TOKEN.
        """
        if not issue_key.strip():
            return JiraIssueOutput(
                key=issue_key, error="issue_key is required, e.g. 'PROJ-123'."
            )

        try:
            credentials = get_jira_credentials()
        except JiraConfigError as e:
            return JiraIssueOutput(key=issue_key, error=str(e))

        payload, fetch_error = await fetch_issue(credentials, issue_key.strip())
        if fetch_error is not None:
            return JiraIssueOutput(key=issue_key, error=fetch_error.message)

        return _normalize_issue(credentials.base_url, issue_key.strip(), payload or {})
