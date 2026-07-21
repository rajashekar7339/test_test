"""Tests for the Jira plugin's login consolidation and 403 auto-retry."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from fid_coder.plugins.jira import commands
from fid_coder.plugins.jira.client import JiraFetchError
from fid_coder.plugins.jira.config import JiraConfigError, JiraCredentials
from fid_coder.plugins.jira.session import JiraLoginError, perform_jira_login


class TestLoginCookieHelpers:
    def test_looks_logged_in_detects_jsessionid(self):
        from fid_coder.plugins.jira.login import _looks_logged_in

        assert _looks_logged_in([{"name": "JSESSIONID", "value": "abc"}])
        assert not _looks_logged_in([{"name": "other", "value": "x"}])

    def test_cookies_for_host_prefers_matching_domain(self):
        from fid_coder.plugins.jira.login import _cookies_for_host

        cookies = [
            {"name": "a", "value": "1", "domain": ".other.com"},
            {"name": "JSESSIONID", "value": "2", "domain": ".jira.example.com"},
        ]
        matched = _cookies_for_host(cookies, "jira.example.com")
        assert matched == [cookies[1]]


class TestPerformJiraLogin:
    def test_raises_when_url_cannot_be_resolved(self):
        with patch(
            "fid_coder.plugins.jira.session.resolve_jira_url", return_value=None
        ):
            with pytest.raises(JiraLoginError, match="Jira URL is not set"):
                perform_jira_login()

    def test_persists_url_before_opening_browser(self):
        with (
            patch(
                "fid_coder.plugins.jira.session.resolve_jira_url",
                return_value="https://jira.example.com",
            ),
            patch("fid_coder.plugins.jira.session.save_section") as mock_save,
            patch("fid_coder.plugins.jira.session.ensure_jira_cookie") as mock_ensure,
            patch("fid_coder.messaging.emit_info"),
        ):
            url = perform_jira_login(url="https://jira.example.com", force=True)

        assert url == "https://jira.example.com"
        mock_save.assert_called_once_with("jira", {"url": "https://jira.example.com"})
        mock_ensure.assert_called_once_with(
            base_url="https://jira.example.com", force=True
        )

    def test_wraps_browser_failure_in_jira_login_error(self):
        with (
            patch(
                "fid_coder.plugins.jira.session.resolve_jira_url",
                return_value="https://jira.example.com",
            ),
            patch("fid_coder.plugins.jira.session.save_section"),
            patch(
                "fid_coder.plugins.jira.session.ensure_jira_cookie",
                side_effect=RuntimeError("boom"),
            ),
            patch("fid_coder.messaging.emit_info"),
        ):
            with pytest.raises(JiraLoginError, match="Browser login failed: boom"):
                perform_jira_login()


class TestJiraCommandHelp:
    def test_help_only_lists_login(self):
        entries = commands.custom_command_help()
        assert entries == [
            (
                "jira login [url]",
                "Open Jira in a browser, capture cookie → authentication.json",
            )
        ]

    def test_status_set_clear_are_no_longer_registered(self):
        entries = dict(commands.custom_command_help())
        assert "jira status" not in entries
        assert "jira set cookie <value>" not in entries
        assert "jira set url <url>" not in entries

    def test_handle_custom_command_ignores_other_names(self):
        assert commands.handle_custom_command("/theme", "theme") is None

    def test_bare_jira_command_defaults_to_login(self):
        with patch.object(commands, "_handle_login", return_value=True) as mock_login:
            result = commands.handle_custom_command("/jira", "jira")

        assert result is True
        mock_login.assert_called_once_with([])

    def test_login_forwards_url_arg(self):
        with (
            patch(
                "fid_coder.plugins.jira.session.perform_jira_login",
                return_value="https://jira.example.com",
            ) as mock_perform,
            patch("fid_coder.messaging.emit_success"),
        ):
            result = commands.handle_custom_command(
                "/jira login https://jira.example.com", "jira"
            )

        assert result is True
        mock_perform.assert_called_once_with(url="https://jira.example.com", force=True)


class TestReadJiraIssueAutoRelogin:
    def _make_agent(self):
        agent = MagicMock()
        registered: dict = {}

        def _tool(func):
            registered["fn"] = func
            return func

        agent.tool = _tool
        return agent, registered

    def test_403_with_cookie_triggers_relogin_and_retries(self):
        from fid_coder.plugins.jira.tools import register_read_jira_issue

        agent, registered = self._make_agent()
        register_read_jira_issue(agent)
        read_jira_issue = registered["fn"]

        creds = JiraCredentials(base_url="https://jira.example.com", cookie="abc")
        forbidden = (None, JiraFetchError(status_code=403, message="forbidden"))
        success_payload = (
            {"key": "PROJ-1", "fields": {"summary": "Test issue"}},
            None,
        )

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.fetch_issue",
                side_effect=[forbidden, success_payload],
            ) as mock_fetch,
            patch("fid_coder.plugins.jira.tools.perform_jira_login") as mock_relogin,
            patch(
                "fid_coder.plugins.jira.tools.refresh_credentials_after_login",
                return_value=creds,
            ),
        ):
            result = asyncio.run(
                read_jira_issue(context=MagicMock(), issue_key="PROJ-1")
            )

        assert mock_fetch.call_count == 2
        mock_relogin.assert_called_once_with(url="https://jira.example.com", force=True)
        assert result.error is None
        assert result.key == "PROJ-1"
        assert result.summary == "Test issue"

    def test_403_without_cookie_does_not_relogin(self):
        from fid_coder.plugins.jira.tools import register_read_jira_issue

        agent, registered = self._make_agent()
        register_read_jira_issue(agent)
        read_jira_issue = registered["fn"]

        creds = JiraCredentials(
            base_url="https://jira.example.com", cookie=None, personal_token="tok"
        )
        forbidden = (None, JiraFetchError(status_code=403, message="forbidden"))

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.fetch_issue",
                return_value=forbidden,
            ) as mock_fetch,
            patch("fid_coder.plugins.jira.tools.perform_jira_login") as mock_relogin,
        ):
            result = asyncio.run(
                read_jira_issue(context=MagicMock(), issue_key="PROJ-1")
            )

        mock_fetch.assert_called_once()
        mock_relogin.assert_not_called()
        assert result.error == "forbidden"

    def test_relogin_failure_surfaces_combined_error(self):
        from fid_coder.plugins.jira.tools import register_read_jira_issue

        agent, registered = self._make_agent()
        register_read_jira_issue(agent)
        read_jira_issue = registered["fn"]

        creds = JiraCredentials(base_url="https://jira.example.com", cookie="abc")
        forbidden = (None, JiraFetchError(status_code=403, message="forbidden"))

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.fetch_issue",
                return_value=forbidden,
            ),
            patch(
                "fid_coder.plugins.jira.tools.perform_jira_login",
                side_effect=JiraLoginError("nope"),
            ),
        ):
            result = asyncio.run(
                read_jira_issue(context=MagicMock(), issue_key="PROJ-1")
            )

        assert "forbidden" in result.error
        assert "Automatic re-login failed: nope" in result.error

    def test_missing_credentials_opens_browser_then_fetches(self):
        from fid_coder.plugins.jira.tools import register_read_jira_issue

        agent, registered = self._make_agent()
        register_read_jira_issue(agent)
        read_jira_issue = registered["fn"]

        creds = JiraCredentials(base_url="https://jira.example.com", cookie="abc")
        success_payload = (
            {"key": "PROJ-1", "fields": {"summary": "Test issue"}},
            None,
        )

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                side_effect=JiraConfigError("no creds"),
            ),
            patch(
                "fid_coder.plugins.jira.tools.perform_jira_login",
                return_value="https://jira.example.com",
            ) as mock_login,
            patch(
                "fid_coder.plugins.jira.tools.refresh_credentials_after_login",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.fetch_issue",
                return_value=success_payload,
            ) as mock_fetch,
        ):
            result = asyncio.run(
                read_jira_issue(context=MagicMock(), issue_key="PROJ-1")
            )

        mock_login.assert_called_once_with(force=True)
        mock_fetch.assert_called_once()
        assert result.error is None
        assert result.key == "PROJ-1"
        assert result.summary == "Test issue"

    def test_missing_credentials_login_failure_surfaces_error(self):
        from fid_coder.plugins.jira.tools import register_read_jira_issue

        agent, registered = self._make_agent()
        register_read_jira_issue(agent)
        read_jira_issue = registered["fn"]

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                side_effect=JiraConfigError("no creds"),
            ),
            patch(
                "fid_coder.plugins.jira.tools.perform_jira_login",
                side_effect=JiraLoginError("browser died"),
            ),
        ):
            result = asyncio.run(
                read_jira_issue(context=MagicMock(), issue_key="PROJ-1")
            )

        assert "automatic login failed" in result.error.lower()
        assert "browser died" in result.error


class TestSearchJiraIssues:
    def _make_agent(self):
        agent = MagicMock()
        registered: dict = {}

        def _tool(func):
            registered["fn"] = func
            return func

        agent.tool = _tool
        return agent, registered

    def test_empty_jql_returns_error(self):
        from fid_coder.plugins.jira.tools import register_search_jira_issues

        agent, registered = self._make_agent()
        register_search_jira_issues(agent)
        search = registered["fn"]

        result = asyncio.run(search(context=MagicMock(), jql="  "))
        assert result.error is not None
        assert "jql is required" in result.error.lower()

    def test_search_normalizes_issues(self):
        from fid_coder.plugins.jira.tools import register_search_jira_issues

        agent, registered = self._make_agent()
        register_search_jira_issues(agent)
        search = registered["fn"]

        creds = JiraCredentials(base_url="https://jira.example.com", cookie="abc")
        payload = (
            {
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
                "issues": [
                    {
                        "key": "PROJ-9",
                        "fields": {
                            "summary": "Child of epic",
                            "status": {"name": "Open"},
                            "issuetype": {"name": "Story"},
                        },
                    }
                ],
            },
            None,
        )

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.search_issues",
                return_value=payload,
            ) as mock_search,
        ):
            result = asyncio.run(
                search(
                    context=MagicMock(),
                    jql='"Epic Link" = PROJ-123 OR parent = PROJ-123',
                    max_results=50,
                )
            )

        mock_search.assert_called_once()
        assert result.error is None
        assert result.total == 1
        assert len(result.issues) == 1
        assert result.issues[0].key == "PROJ-9"
        assert result.issues[0].summary == "Child of epic"
        assert result.issues[0].url == "https://jira.example.com/browse/PROJ-9"

    def test_search_403_with_cookie_retries(self):
        from fid_coder.plugins.jira.tools import register_search_jira_issues

        agent, registered = self._make_agent()
        register_search_jira_issues(agent)
        search = registered["fn"]

        creds = JiraCredentials(base_url="https://jira.example.com", cookie="abc")
        forbidden = (None, JiraFetchError(status_code=403, message="forbidden"))
        success = (
            {"total": 0, "startAt": 0, "maxResults": 50, "issues": []},
            None,
        )

        with (
            patch(
                "fid_coder.plugins.jira.tools.get_jira_credentials",
                return_value=creds,
            ),
            patch(
                "fid_coder.plugins.jira.tools.search_issues",
                side_effect=[forbidden, success],
            ) as mock_search,
            patch("fid_coder.plugins.jira.tools.perform_jira_login") as mock_login,
            patch(
                "fid_coder.plugins.jira.tools.refresh_credentials_after_login",
                return_value=creds,
            ),
        ):
            result = asyncio.run(
                search(context=MagicMock(), jql="project = PROJ", max_results=10)
            )

        assert mock_search.call_count == 2
        mock_login.assert_called_once_with(url="https://jira.example.com", force=True)
        assert result.error is None
        assert result.total == 0
