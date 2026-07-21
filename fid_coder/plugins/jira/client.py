"""Thin async REST client for Jira read/search.

Endpoints used:
- ``GET  /rest/api/2/issue/{key}`` — single issue
- ``POST /rest/api/2/search`` — JQL search

Write/transition support is intentionally out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from .config import JiraCredentials

REQUEST_TIMEOUT_S = 15.0

# Fields returned for list/search results (keep payloads small).
_SEARCH_FIELDS = [
    "summary",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "reporter",
    "labels",
    "created",
    "updated",
    "description",
    "parent",
]

JiraResult = tuple[Optional[dict[str, Any]], Optional["JiraFetchError"]]


@dataclass
class JiraFetchError:
    """Structured error returned instead of raising, so tools stay crash-free."""

    status_code: Optional[int]
    message: str


def _auth_headers(credentials: JiraCredentials) -> dict[str, str]:
    return {"Accept": "application/json", **credentials.request_headers}


def _http_error(response: httpx.Response, *, context: str) -> JiraResult:
    if response.status_code == 401:
        return None, JiraFetchError(
            status_code=401,
            message="Jira rejected the credentials (401 Unauthorized). "
            "Session likely expired — ask me to log in to Jira again "
            "(or check JIRA_PERSONAL_TOKEN / JIRA_EMAIL+JIRA_API_TOKEN).",
        )
    if response.status_code == 403:
        return None, JiraFetchError(
            status_code=403,
            message=f"{context} is forbidden (403). Your account may lack permission.",
        )
    if response.status_code == 404:
        return None, JiraFetchError(
            status_code=404,
            message=f"{context} was not found (404).",
        )
    if 300 <= response.status_code < 400:
        location = response.headers.get("location", "")
        return None, JiraFetchError(
            status_code=response.status_code,
            message=(
                f"Jira returned HTTP {response.status_code} after redirects"
                + (f" (Location: {location})" if location else "")
                + ". Prefer https:// in jira.url — try "
                "`/jira login https://jira.<company>.com`."
            ),
        )
    return None, JiraFetchError(
        status_code=response.status_code,
        message=f"Jira returned HTTP {response.status_code}: {response.text[:300]}",
    )


async def _request(
    credentials: JiraCredentials,
    method: str,
    path: str,
    *,
    json_body: Optional[dict[str, Any]] = None,
) -> tuple[Optional[httpx.Response], Optional[JiraFetchError]]:
    """Issue one authed request; map transport failures to JiraFetchError."""
    url = f"{credentials.base_url}{path}"
    headers = _auth_headers(credentials)
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    try:
        # follow_redirects: corporate Jira often stores http:// and 301s to https://
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_S, follow_redirects=True
        ) as client:
            response = await client.request(
                method, url, headers=headers, json=json_body
            )
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
    return response, None


def _parse_json(response: httpx.Response) -> JiraResult:
    try:
        return response.json(), None
    except ValueError as e:
        return None, JiraFetchError(
            status_code=response.status_code,
            message=f"Jira returned an unparseable response: {e}",
        )


async def fetch_issue(credentials: JiraCredentials, issue_key: str) -> JiraResult:
    """Fetch raw issue JSON from Jira's REST API.

    Returns ``(payload, None)`` on success or ``(None, error)`` on failure.
    Never raises for expected HTTP failures (401/403/404/timeout).
    """
    response, error = await _request(
        credentials, "GET", f"/rest/api/2/issue/{issue_key}"
    )
    if error is not None or response is None:
        return None, error

    if response.status_code == 200:
        return _parse_json(response)

    return _http_error(response, context=f"Issue '{issue_key}'")


async def search_issues(
    credentials: JiraCredentials,
    jql: str,
    *,
    max_results: int = 50,
    start_at: int = 0,
) -> JiraResult:
    """Run a JQL search via ``POST /rest/api/2/search``.

    Returns ``(payload, None)`` on success where payload includes ``issues``,
    ``total``, ``startAt``, ``maxResults``. On failure ``(None, error)``.
    """
    body = {
        "jql": jql,
        "startAt": max(0, start_at),
        "maxResults": max(1, min(max_results, 100)),
        "fields": _SEARCH_FIELDS,
    }
    response, error = await _request(
        credentials, "POST", "/rest/api/2/search", json_body=body
    )
    if error is not None or response is None:
        return None, error

    if response.status_code == 200:
        return _parse_json(response)

    # JQL syntax errors often come back as 400 with a useful errorMessages list.
    if response.status_code == 400:
        detail = response.text[:300]
        try:
            data = response.json()
            messages = data.get("errorMessages") or []
            if messages:
                detail = "; ".join(str(m) for m in messages)
        except ValueError:
            pass
        return None, JiraFetchError(status_code=400, message=f"Invalid JQL: {detail}")

    return _http_error(response, context="Jira search")
