"""Tests for fid_coder/tools/__init__.py - 100% coverage."""

from unittest.mock import MagicMock, patch


class TestLoadPluginTools:
    def test_loads_tools(self):
        from fid_coder.tools import TOOL_REGISTRY, _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools") as mock_cb:
            mock_cb.return_value = [
                [{"name": "test_tool", "register_func": lambda a: None}]
            ]
            _load_plugin_tools()
            assert "test_tool" in TOOL_REGISTRY
            del TOOL_REGISTRY["test_tool"]

    def test_none_results(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools") as mock_cb:
            mock_cb.return_value = [None]
            _load_plugin_tools()  # should not raise

    def test_single_dict_result(self):
        from fid_coder.tools import TOOL_REGISTRY, _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools") as mock_cb:
            mock_cb.return_value = [
                {"name": "single_tool", "register_func": lambda a: None}
            ]
            _load_plugin_tools()
            assert "single_tool" in TOOL_REGISTRY
            del TOOL_REGISTRY["single_tool"]

    def test_invalid_tool_def(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools") as mock_cb:
            mock_cb.return_value = [[{"name": "no_func"}]]  # missing register_func
            _load_plugin_tools()  # should not raise

    def test_non_callable(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools") as mock_cb:
            mock_cb.return_value = [[{"name": "x", "register_func": "not_callable"}]]
            _load_plugin_tools()  # should not add

    def test_exception_swallowed(self):
        from fid_coder.tools import _load_plugin_tools

        with patch("fid_coder.tools.on_register_tools", side_effect=Exception("boom")):
            _load_plugin_tools()  # should not raise


class TestHasExtendedThinkingActive:
    @patch("fid_coder.config.get_global_model_name", return_value=None)
    def test_no_model(self, mock_model):
        from fid_coder.tools import has_extended_thinking_active

        assert not has_extended_thinking_active()

    def test_non_claude(self):
        from fid_coder.tools import has_extended_thinking_active

        assert not has_extended_thinking_active("gpt-4")

    @patch("fid_coder.config.get_effective_model_settings", return_value={})
    @patch("fid_coder.model_utils.get_default_extended_thinking", return_value=False)
    def test_claude_disabled(self, mock_default, mock_settings):
        from fid_coder.tools import has_extended_thinking_active

        assert not has_extended_thinking_active("claude-3")

    @patch(
        "fid_coder.config.get_effective_model_settings",
        return_value={"extended_thinking": True},
    )
    @patch("fid_coder.model_utils.get_default_extended_thinking", return_value=False)
    def test_claude_legacy_true(self, mock_default, mock_settings):
        from fid_coder.tools import has_extended_thinking_active

        assert has_extended_thinking_active("claude-3")

    @patch(
        "fid_coder.config.get_effective_model_settings",
        return_value={"extended_thinking": "enabled"},
    )
    @patch("fid_coder.model_utils.get_default_extended_thinking", return_value=False)
    def test_claude_enabled(self, mock_default, mock_settings):
        from fid_coder.tools import has_extended_thinking_active

        assert has_extended_thinking_active("claude-3")

    @patch(
        "fid_coder.config.get_effective_model_settings",
        return_value={"extended_thinking": "adaptive"},
    )
    @patch("fid_coder.model_utils.get_default_extended_thinking", return_value=False)
    def test_claude_adaptive(self, mock_default, mock_settings):
        from fid_coder.tools import has_extended_thinking_active

        assert has_extended_thinking_active("anthropic-model")


class TestRegisterToolsForAgent:
    @patch("fid_coder.tools._load_plugin_tools")
    @patch("fid_coder.tools.has_extended_thinking_active", return_value=False)
    def test_register_known_tool(self, mock_ext, mock_load):
        from fid_coder.tools import TOOL_REGISTRY, register_tools_for_agent

        agent = MagicMock()
        mock_fn = MagicMock()
        TOOL_REGISTRY["__test_tool"] = mock_fn
        try:
            register_tools_for_agent(agent, ["__test_tool"])
            mock_fn.assert_called_once_with(agent)
        finally:
            del TOOL_REGISTRY["__test_tool"]

    @patch("fid_coder.tools._load_plugin_tools")
    @patch("fid_coder.tools.has_extended_thinking_active", return_value=False)
    @patch("fid_coder.tools.emit_warning")
    def test_unknown_tool(self, mock_warn, mock_ext, mock_load):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        register_tools_for_agent(agent, ["__nonexistent_tool"])
        mock_warn.assert_called()

    @patch("fid_coder.tools._load_plugin_tools")
    @patch("fid_coder.tools.has_extended_thinking_active", return_value=False)
    def test_register_legacy_reasoning_tool(self, mock_ext, mock_load):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        register_tools_for_agent(agent, ["agent_share_your_reasoning"])
        agent.tool.assert_called()

    @patch("fid_coder.tools._load_plugin_tools")
    @patch("fid_coder.tools.has_extended_thinking_active", return_value=False)
    @patch("fid_coder.config.get_universal_constructor_enabled", return_value=False)
    def test_skip_uc_disabled(self, mock_uc, mock_ext, mock_load):
        from fid_coder.tools import TOOL_REGISTRY, register_tools_for_agent

        mock_fn = MagicMock()
        original = TOOL_REGISTRY.get("universal_constructor")
        TOOL_REGISTRY["universal_constructor"] = mock_fn
        try:
            agent = MagicMock()
            register_tools_for_agent(agent, ["universal_constructor"])
            mock_fn.assert_not_called()
        finally:
            if original:
                TOOL_REGISTRY["universal_constructor"] = original

    @patch("fid_coder.tools._load_plugin_tools")
    @patch("fid_coder.tools.has_extended_thinking_active", return_value=False)
    @patch("fid_coder.config.get_universal_constructor_enabled", return_value=False)
    def test_skip_uc_prefixed_disabled(self, mock_uc, mock_ext, mock_load):
        from fid_coder.tools import register_tools_for_agent

        agent = MagicMock()
        register_tools_for_agent(agent, ["uc:api.weather"])
        # Should skip silently


class TestRegisterAllToolsAndGetNames:
    @patch("fid_coder.tools.register_tools_for_agent")
    def test_register_all(self, mock_reg):
        from fid_coder.tools import register_all_tools

        agent = MagicMock()
        register_all_tools(agent, model_name="test")
        mock_reg.assert_called_once()

    @patch("fid_coder.tools._load_plugin_tools")
    def test_get_names(self, mock_load):
        from fid_coder.tools import get_available_tool_names

        names = get_available_tool_names()
        assert isinstance(names, list)
        assert len(names) > 0


class TestExtendedThinkingPromptNote:
    def test_constant_exists(self):
        from fid_coder.tools import EXTENDED_THINKING_PROMPT_NOTE

        assert "extended thinking" in EXTENDED_THINKING_PROMPT_NOTE.lower()
