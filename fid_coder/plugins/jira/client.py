"""Thin async REST client for reading Jira issues.

Deliberately minimal: one GET against ``/rest/api/2/issue/{key}``. No
write/search/transition support (out of scope for this first slice).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from .config import JiraCredentials

REQUEST_TIMEOUT_S = 15.0


@dataclass
class JiraFetchError:
    """Structured error returned instead of raising, so tools stay crash-free."""

    status_code: Optional[int]
    message: str


async def fetch_issue(
    credentials: JiraCredentials, issue_key: str
) -> tuple[Optional[dict[str, Any]], Optional[JiraFetchError]]:
    """Fetch raw issue JSON from Jira's REST API.

    Returns ``(payload, None)`` on success or ``(None, error)`` on failure.
    Never raises for expected HTTP failures (401/403/404/timeout).
    """
    url = f"{credentials.base_url}/rest/api/2/issue/{issue_key}"
    headers = {"Accept": "application/json", **credentials.auth_header}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        return None, JiraFetchError(
            status_code=None,
            message=f"Timed out contacting {credentials.base_url} after {REQUEST_TIMEOUT_S}s.",
        )
    except httpx.RequestError as e:
        return None, JiraFetchError(
            status_code=None,
            message=f"Could not reach {credentials.base_url}: {e}",
        )

    if response.status_code == 200:
        try:
            return response.json(), None
        except ValueError as e:
            return None, JiraFetchError(
                status_code=response.status_code,
                message=f"Jira returned an unparseable response: {e}",
            )

    if response.status_code == 401:
        return None, JiraFetchError(
            status_code=401,
            message="Jira rejected the credentials (401 Unauthorized). "
            "Check JIRA_EMAIL/JIRA_API_TOKEN or JIRA_PERSONAL_TOKEN.",
        )
    if response.status_code == 403:
        return None, JiraFetchError(
            status_code=403,
            message=f"Access to issue '{issue_key}' is forbidden (403). "
            "Your account may lack permission to view it.",
        )
    if response.status_code == 404:
        return None, JiraFetchError(
            status_code=404,
            message=f"Issue '{issue_key}' was not found (404). Check the key and base URL.",
        )

    return None, JiraFetchError(
        status_code=response.status_code,
        message=f"Jira returned HTTP {response.status_code}: {response.text[:300]}",
    )
