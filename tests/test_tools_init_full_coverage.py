"""Full coverage tests for tools/__init__.py."""

from unittest.mock import MagicMock, patch


class TestToolRegistry:
    def test_tool_registry_populated(self):
        from fid_coder.tools import TOOL_REGISTRY

        assert "list_files" in TOOL_REGISTRY
        assert "edit_file" in TOOL_REGISTRY

    def test_get_available_tool_names(self):
        from fid_coder.tools import get_available_tool_names

        names = get_available_tool_names()
        assert isinstance(names, list)
        assert "read_file" in names


class TestLoadPluginTools:
    def test_load_plugin_tools_success(self):
        from fid_coder.tools import _load_plugin_tools

        _load_plugin_tools()  # Should not crash

    def test_load_plugin_tools_with_result(self):
        from fid_coder.tools import TOOL_REGISTRY, _load_plugin_tools

        mock_fn = MagicMock()
        with patch(
            "fid_coder.tools.on_register_tools",
            return_value=[[{"name": "test_plugin_tool", "register_func": mock_fn}]],
        ):
            _load_plugin_tools()
            assert "test_plugin_tool" in TOOL_REGISTRY
            del TOOL_REGISTRY["test_plugin_tool"]

    def test_load_plugin_tools_none_result(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools", return_value=[None]):
            _load_plugin_tools()

    def test_load_plugin_tools_exception(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools", side_effect=Exception("boom")):
            _load_plugin_tools()  # Should not raise

    def test_load_plugin_tools_invalid_tool_def(self):
        from fid_coder.tools import _load_plugin_tools

        with patch(
            "fid_coder.tools.on_register_tools", return_value=[[{"invalid": True}]]
        ):
            _load_plugin_tools()  # Should not crash


class TestHasExtendedThinkingActive:
    def test_none_model(self):
        from fid_coder.tools import has_extended_thinking_active

        with patch("fid_coder.config.get_global_model_name", return_value=None):
            assert has_extended_thinking_active() is False

    def test_non_anthropic_model(self):
        from fid_coder.tools import has_extended_thinking_active

        assert has_extended_thinking_active("gpt-4") is False

    def test_anthropic_model_enabled(self):
        from fid_coder.tools import has_extended_thinking_active

        with (
            patch(
                "fid_coder.config.get_effective_model_settings",
                return_value={"extended_thinking": "enabled"},
            ),
            patch(
                "fid_coder.model_utils.get_default_extended_thinking",
                return_value=False,
            ),
        ):
            assert has_extended_thinking_active("claude-3") is True

    def test_anthropic_model_adaptive(self):
        from fid_coder.tools import has_extended_thinking_active

        with (
            patch(
                "fid_coder.config.get_effective_model_settings",
                return_value={"extended_thinking": "adaptive"},
            ),
            patch(
                "fid_coder.model_utils.get_default_extended_thinking",
                return_value=False,
            ),
        ):
            assert has_extended_thinking_active("claude-3") is True

    def test_anthropic_model_disabled(self):
        from fid_coder.tools import has_extended_thinking_active

        with (
            patch(
                "fid_coder.config.get_effective_model_settings",
                return_value={"extended_thinking": False},
            ),
            patch(
                "fid_coder.model_utils.get_default_extended_thinking",
                return_value=False,
            ),
        ):
            assert has_extended_thinking_active("claude-3") is False

    def test_anthropic_model_legacy_true(self):
        from fid_coder.tools import has_extended_thinking_active

        with (
            patch(
                "fid_coder.config.get_effective_model_settings",
                return_value={"extended_thinking": True},
            ),
            patch(
                "fid_coder.model_utils.get_default_extended_thinking",
                return_value=False,
            ),
        ):
            assert has_extended_thinking_active("claude-3") is True

    def test_anthropic_prefix(self):
        from fid_coder.tools import has_extended_thinking_active

        with (
            patch(
                "fid_coder.config.get_effective_model_settings",
                return_value={"extended_thinking": "enabled"},
            ),
            patch(
                "fid_coder.model_utils.get_default_extended_thinking",
                return_value=False,
            ),
        ):
            assert has_extended_thinking_active("anthropic-model") is True


class TestRegisterToolsForAgent:
    def test_register_known_tools(self):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        agent.tool_plain = lambda fn: fn
        agent.tool = lambda fn: fn
        register_tools_for_agent(agent, ["list_files"])

    def test_register_unknown_tool(self):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        with patch("fid_coder.tools.emit_warning"):
            register_tools_for_agent(agent, ["nonexistent_tool_xyz"])

    def test_skip_uc_when_disabled(self):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        with patch(
            "fid_coder.config.get_universal_constructor_enabled", return_value=False
        ):
            register_tools_for_agent(agent, ["universal_constructor"])

    def test_skip_removed_reasoning_tool(self):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        with (
            patch("fid_coder.tools.emit_warning") as mock_warn,
            patch(
                "fid_coder.config.get_universal_constructor_enabled", return_value=True
            ),
        ):
            register_tools_for_agent(agent, ["agent_share_your_reasoning"])
            mock_warn.assert_not_called()


class TestRegisterAllTools:
    def test_register_all(self):
        from fid_coder.tools import register_all_tools

        agent = MagicMock()
        agent.tool_plain = lambda fn: fn
        agent.tool = lambda fn: fn
        with patch(
            "fid_coder.config.get_universal_constructor_enabled", return_value=False
        ):
            register_all_tools(agent)
