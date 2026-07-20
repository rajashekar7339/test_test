"""Tests for agent-name helpers in agent_completion_helpers.py."""

from unittest.mock import mock_open, patch


class TestGetPinnedModelForAgent:
    def test_from_config(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_pinned_model_for_agent,
        )

        with patch("fid_coder.config.get_agent_pinned_model", return_value="gpt-4"):
            assert _get_pinned_model_for_agent("test") == "gpt-4"

    def test_from_json_agent(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_pinned_model_for_agent,
        )

        with (
            patch("fid_coder.config.get_agent_pinned_model", return_value=None),
            patch(
                "fid_coder.agents.json_agent.discover_json_agents",
                return_value={"myagent": "/tmp/a.json"},
            ),
            patch(
                "builtins.open",
                mock_open(read_data='{"model": "claude-3"}'),
            ),
        ):
            assert _get_pinned_model_for_agent("myagent") == "claude-3"

    def test_not_found(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_pinned_model_for_agent,
        )

        with (
            patch("fid_coder.config.get_agent_pinned_model", return_value=None),
            patch(
                "fid_coder.agents.json_agent.discover_json_agents",
                return_value={},
            ),
        ):
            assert _get_pinned_model_for_agent("unknown") is None

    def test_config_exception(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_pinned_model_for_agent,
        )

        with (
            patch(
                "fid_coder.config.get_agent_pinned_model",
                side_effect=Exception("fail"),
            ),
            patch(
                "fid_coder.agents.json_agent.discover_json_agents",
                side_effect=Exception("fail2"),
            ),
        ):
            assert _get_pinned_model_for_agent("x") is None


class TestGetAgentDisplayMeta:
    def test_with_pinned_model(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_agent_display_meta,
        )

        with patch(
            "fid_coder.command_line.agent_completion_helpers._get_pinned_model_for_agent",
            return_value="gpt-4",
        ):
            assert _get_agent_display_meta("test") == "→ gpt-4"

    def test_without_pinned_model(self):
        from fid_coder.command_line.agent_completion_helpers import (
            _get_agent_display_meta,
        )

        with patch(
            "fid_coder.command_line.agent_completion_helpers._get_pinned_model_for_agent",
            return_value=None,
        ):
            assert _get_agent_display_meta("test") == "default"


class TestLoadAgentNames:
    def test_combines_builtin_and_json(self):
        from fid_coder.command_line.agent_completion_helpers import load_agent_names

        with (
            patch(
                "fid_coder.agents.agent_manager.get_agent_descriptions",
                return_value={"builtin1": "desc"},
            ),
            patch(
                "fid_coder.agents.json_agent.discover_json_agents",
                return_value={"json1": "/tmp/j1.json"},
            ),
        ):
            result = load_agent_names()
            assert "builtin1" in result
            assert "json1" in result
            assert result == sorted(result)

    def test_handles_exceptions(self):
        from fid_coder.command_line.agent_completion_helpers import load_agent_names

        with (
            patch(
                "fid_coder.agents.agent_manager.get_agent_descriptions",
                side_effect=Exception("fail"),
            ),
            patch(
                "fid_coder.agents.json_agent.discover_json_agents",
                side_effect=Exception("fail"),
            ),
        ):
            assert load_agent_names() == []
