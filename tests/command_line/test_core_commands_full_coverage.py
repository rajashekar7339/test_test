"""Full coverage tests for fid_coder/command_line/core_commands.py."""

import os
from unittest.mock import MagicMock, patch


class TestGetCommandsHelp:
    def test_lazy_import(self):
        from fid_coder.command_line.core_commands import get_commands_help

        with patch(
            "fid_coder.command_line.command_handler.get_commands_help",
            return_value="help",
        ):
            assert get_commands_help() == "help"


class TestHandleHelpCommand:
    def test_help(self):
        from fid_coder.command_line.core_commands import handle_help_command

        with (
            patch(
                "fid_coder.command_line.core_commands.get_commands_help",
                return_value="help text",
            ),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_help_command("/help") is True


class TestHandleCdCommand:
    def test_no_args_lists_dir(self):
        from fid_coder.command_line.core_commands import handle_cd_command

        with (
            patch(
                "fid_coder.command_line.core_commands.make_directory_table",
                return_value="table",
            ),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_cd_command("/cd") is True

    def test_no_args_error(self):
        from fid_coder.command_line.core_commands import handle_cd_command

        with (
            patch(
                "fid_coder.command_line.core_commands.make_directory_table",
                side_effect=Exception("fail"),
            ),
            patch("fid_coder.messaging.emit_error"),
        ):
            assert handle_cd_command("/cd") is True

    def test_cd_valid_dir(self, tmp_path):
        from fid_coder.command_line.core_commands import handle_cd_command

        original = os.getcwd()
        try:
            with patch("fid_coder.messaging.emit_success"):
                assert handle_cd_command(f"/cd {tmp_path}") is True
                assert os.getcwd() == str(tmp_path)
        finally:
            os.chdir(original)

    def test_cd_invalid_dir(self):
        from fid_coder.command_line.core_commands import handle_cd_command

        with patch("fid_coder.messaging.emit_error"):
            assert handle_cd_command("/cd /nonexistent/dir/xyz") is True

    def test_cd_quoted_path(self, tmp_path):
        from fid_coder.command_line.core_commands import handle_cd_command

        original = os.getcwd()
        try:
            with patch("fid_coder.messaging.emit_success"):
                assert handle_cd_command(f'/cd "{tmp_path}"') is True
        finally:
            os.chdir(original)

    def test_cd_too_many_args(self):
        from fid_coder.command_line.core_commands import handle_cd_command

        assert handle_cd_command("/cd a b c") is True


class TestHandleToolsCommand:
    def test_tools(self):
        from fid_coder.command_line.core_commands import handle_tools_command

        with patch("fid_coder.messaging.emit_info"):
            assert handle_tools_command("/tools") is True


class TestHandlePasteCommand:
    def test_no_image(self):
        from fid_coder.command_line.core_commands import handle_paste_command

        with (
            patch(
                "fid_coder.command_line.clipboard.has_image_in_clipboard",
                return_value=False,
            ),
            patch("fid_coder.messaging.emit_warning"),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_paste_command("/paste") is True

    def test_success(self):
        from fid_coder.command_line.core_commands import handle_paste_command

        mock_mgr = MagicMock()
        mock_mgr.get_pending_count.return_value = 1
        with (
            patch(
                "fid_coder.command_line.clipboard.has_image_in_clipboard",
                return_value=True,
            ),
            patch(
                "fid_coder.command_line.clipboard.capture_clipboard_image_to_pending",
                return_value="img.png",
            ),
            patch(
                "fid_coder.command_line.clipboard.get_clipboard_manager",
                return_value=mock_mgr,
            ),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_paste_command("/paste") is True

    def test_failure(self):
        from fid_coder.command_line.core_commands import handle_paste_command

        with (
            patch(
                "fid_coder.command_line.clipboard.has_image_in_clipboard",
                return_value=True,
            ),
            patch(
                "fid_coder.command_line.clipboard.capture_clipboard_image_to_pending",
                return_value=None,
            ),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_paste_command("/paste") is True


class TestHandleTutorialCommand:
    def test_copilot(self):
        from fid_coder.command_line.core_commands import handle_tutorial_command

        with (
            patch("fid_coder.command_line.onboarding_wizard.reset_onboarding"),
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.messaging.emit_info"),
            patch(
                "fid_coder.plugins.copilot_auth.register_callbacks._handle_copilot_login"
            ),
            patch(
                "fid_coder.command_line.onboarding_wizard.require_model_setup_if_needed"
            ),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "copilot"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_tutorial_command("/tutorial") is True

    def test_completed(self):
        from fid_coder.command_line.core_commands import handle_tutorial_command

        with (
            patch("fid_coder.command_line.onboarding_wizard.reset_onboarding"),
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.messaging.emit_info"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "completed"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_tutorial_command("/tutorial") is True

    def test_skipped(self):
        from fid_coder.command_line.core_commands import handle_tutorial_command

        with (
            patch("fid_coder.command_line.onboarding_wizard.reset_onboarding"),
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.messaging.emit_info"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "skipped"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_tutorial_command("/tutorial") is True


class TestHandleExitCommand:
    def test_exit(self):
        from fid_coder.command_line.core_commands import handle_exit_command

        with patch("fid_coder.messaging.emit_success"):
            assert handle_exit_command("/exit") is True

    def test_exit_error(self):
        from fid_coder.command_line.core_commands import handle_exit_command

        with patch("fid_coder.messaging.emit_success", side_effect=Exception):
            assert handle_exit_command("/exit") is True


class TestHandleAgentCommand:
    def _mock_agent(self, name="fid-coder", display="Fid Coder", desc="A dog"):
        a = MagicMock()
        a.name = name
        a.display_name = display
        a.description = desc
        return a

    def test_no_args_interactive_select(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        new_agent = self._mock_agent("other", "Other", "Another")
        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch(
                "fid_coder.agents.get_current_agent",
                side_effect=[agent, new_agent, new_agent],
            ),
            patch(
                "fid_coder.command_line.core_commands.finalize_autosave_session",
                return_value="sess1",
            ),
            patch("fid_coder.agents.set_current_agent", return_value=True),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "other"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_agent_command("/agent") is True

    def test_no_args_cancelled(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.messaging.emit_warning"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = None
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_agent_command("/agent") is True

    def test_no_args_already_current(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.agents.get_current_agent", return_value=agent),
            patch("fid_coder.messaging.emit_info"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "fid-coder"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_agent_command("/agent") is True

    def test_no_args_switch_fails(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.agents.get_current_agent", return_value=agent),
            patch(
                "fid_coder.command_line.core_commands.finalize_autosave_session",
                return_value="s",
            ),
            patch("fid_coder.agents.set_current_agent", return_value=False),
            patch("fid_coder.messaging.emit_warning"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "new-agent"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_agent_command("/agent") is True

    def test_no_args_picker_fails_fallback(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        with (
            patch(
                "concurrent.futures.ThreadPoolExecutor", side_effect=Exception("fail")
            ),
            patch("fid_coder.agents.get_current_agent", return_value=agent),
            patch(
                "fid_coder.agents.get_available_agents",
                return_value={"fid-coder": "Fid Coder"},
            ),
            patch(
                "fid_coder.agents.get_agent_descriptions",
                return_value={"fid-coder": "desc"},
            ),
            patch("fid_coder.messaging.emit_warning"),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_agent_command("/agent") is True

    def test_with_name_switch(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        new_agent = self._mock_agent("other", "Other", "desc")
        with (
            patch(
                "fid_coder.agents.get_current_agent",
                side_effect=[agent, new_agent, new_agent],
            ),
            patch(
                "fid_coder.agents.get_available_agents",
                return_value={"fid-coder": "CP", "other": "Other"},
            ),
            patch(
                "fid_coder.command_line.core_commands.finalize_autosave_session",
                return_value="s",
            ),
            patch("fid_coder.agents.set_current_agent", return_value=True),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_agent_command("/agent other") is True

    def test_with_name_not_found(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        with (
            patch(
                "fid_coder.agents.get_available_agents",
                return_value={"fid-coder": "CP"},
            ),
            patch("fid_coder.messaging.emit_error"),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_agent_command("/agent nonexistent") is True

    def test_with_name_already_current(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        with (
            patch("fid_coder.agents.get_current_agent", return_value=agent),
            patch(
                "fid_coder.agents.get_available_agents",
                return_value={"fid-coder": "CP"},
            ),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_agent_command("/agent fid-coder") is True

    def test_with_name_switch_fails(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        agent = self._mock_agent()
        with (
            patch("fid_coder.agents.get_current_agent", return_value=agent),
            patch(
                "fid_coder.agents.get_available_agents",
                return_value={"fid-coder": "CP", "other": "O"},
            ),
            patch(
                "fid_coder.command_line.core_commands.finalize_autosave_session",
                return_value="s",
            ),
            patch("fid_coder.agents.set_current_agent", return_value=False),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_agent_command("/agent other") is True

    def test_too_many_args(self):
        from fid_coder.command_line.core_commands import handle_agent_command

        with patch("fid_coder.messaging.emit_warning"):
            assert handle_agent_command("/agent a b c") is True


class TestHandleModelCommand:
    def test_no_args_interactive_select(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.command_line.model_picker_completion.set_active_model"),
            patch("fid_coder.messaging.emit_success"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = "gpt-5"
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_model_command("/model") is True

    def test_no_args_cancelled(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch("concurrent.futures.ThreadPoolExecutor") as pool,
            patch("fid_coder.messaging.emit_warning"),
        ):
            mock_future = MagicMock()
            mock_future.result.return_value = None
            pool.return_value.__enter__ = MagicMock(return_value=pool.return_value)
            pool.return_value.__exit__ = MagicMock(return_value=False)
            pool.return_value.submit.return_value = mock_future
            assert handle_model_command("/model") is True

    def test_no_args_picker_fails(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch(
                "concurrent.futures.ThreadPoolExecutor", side_effect=Exception("fail")
            ),
            patch(
                "fid_coder.command_line.model_picker_completion.load_model_names",
                return_value=["m1"],
            ),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_model_command("/model") is True

    def test_with_model_name_matched(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch(
                "fid_coder.command_line.core_commands.update_model_in_input",
                return_value="done",
            ),
            patch(
                "fid_coder.command_line.model_picker_completion.get_active_model",
                return_value="gpt-5",
            ),
            patch("fid_coder.messaging.emit_success"),
        ):
            assert handle_model_command("/model gpt-5") is True

    def test_with_model_name_not_matched(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch(
                "fid_coder.command_line.core_commands.update_model_in_input",
                return_value=None,
            ),
            patch(
                "fid_coder.command_line.model_picker_completion.load_model_names",
                return_value=["m1"],
            ),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_model_command("/model bad") is True

    def test_with_model_prefix_conversion(self):
        from fid_coder.command_line.core_commands import handle_model_command

        with (
            patch(
                "fid_coder.command_line.core_commands.update_model_in_input",
                return_value="done",
            ),
            patch(
                "fid_coder.command_line.model_picker_completion.get_active_model",
                return_value="gpt-5",
            ),
            patch("fid_coder.messaging.emit_success"),
        ):
            assert handle_model_command("/m gpt-5") is True


class TestHandleAddModelCommand:
    def test_points_to_copilot_login(self):
        from fid_coder.command_line.core_commands import handle_add_model_command

        with patch("fid_coder.command_line.core_commands.emit_info") as mock_info:
            assert handle_add_model_command("/add_model") is True
            assert "copilot-login" in str(mock_info.call_args)


class TestHandleModelSettingsCommand:
    def test_show_flag(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        with patch(
            "fid_coder.command_line.model_settings_menu.show_model_settings_summary"
        ):
            assert handle_model_settings_command("/model_settings --show") is True

    def test_show_flag_with_model(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        with patch(
            "fid_coder.command_line.model_settings_menu.show_model_settings_summary"
        ) as show:
            assert handle_model_settings_command("/model_settings --show gpt-5") is True
            show.assert_called_once_with("gpt-5")

    def test_interactive_success(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.tools.command_runner.set_awaiting_user_input"),
            patch(
                "fid_coder.command_line.model_settings_menu.interactive_model_settings",
                return_value=True,
            ),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_model_settings_command("/model_settings") is True

    def test_interactive_keyboard_interrupt(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.tools.command_runner.set_awaiting_user_input"),
            patch(
                "fid_coder.command_line.model_settings_menu.interactive_model_settings",
                side_effect=KeyboardInterrupt,
            ),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
            patch("fid_coder.messaging.emit_info"),
        ):
            assert handle_model_settings_command("/model_settings") is True

    def test_interactive_error(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        with (
            patch("fid_coder.tools.command_runner.set_awaiting_user_input"),
            patch(
                "fid_coder.command_line.model_settings_menu.interactive_model_settings",
                side_effect=Exception("fail"),
            ),
            patch("fid_coder.messaging.emit_error"),
        ):
            assert handle_model_settings_command("/model_settings") is False

    def test_reload_failure(self):
        from fid_coder.command_line.core_commands import handle_model_settings_command

        mock_agent = MagicMock()
        mock_agent.reload_code_generation_agent.side_effect = Exception("boom")
        with (
            patch("fid_coder.tools.command_runner.set_awaiting_user_input"),
            patch(
                "fid_coder.command_line.model_settings_menu.interactive_model_settings",
                return_value=False,
            ),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
            patch("fid_coder.messaging.emit_warning"),
        ):
            assert handle_model_settings_command("/model_settings") is True


class TestHandlePlanCommand:
    def test_plan_with_goal_returns_prompt(self):
        from fid_coder.command_line.core_commands import handle_plan_command

        result = handle_plan_command("/plan add retry logic to network client")
        assert isinstance(result, str)
        assert "plan-only mode" in result
        assert "add retry logic" in result

    def test_plan_without_goal_emits_usage(self):
        from fid_coder.command_line.core_commands import handle_plan_command

        with patch("fid_coder.command_line.core_commands.emit_error") as mock_error:
            result = handle_plan_command("/plan")

        assert result is True
        mock_error.assert_called_once_with("Usage: /plan <goal>")


class TestHandleGeneratePrDescription:
    def test_basic(self):
        from fid_coder.command_line.core_commands import (
            handle_generate_pr_description_command,
        )

        result = handle_generate_pr_description_command("/generate-pr-description")
        assert isinstance(result, str)
        assert "PR description" in result

    def test_with_dir(self):
        from fid_coder.command_line.core_commands import (
            handle_generate_pr_description_command,
        )

        result = handle_generate_pr_description_command(
            "/generate-pr-description @src/auth"
        )
        assert "src/auth" in result


class TestHandleWiggumCommand:
    def test_no_prompt(self):
        from fid_coder.plugins.wiggum.register_callbacks import (
            handle_wiggum_command,
        )

        with (
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_warning"),
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_info"),
        ):
            assert handle_wiggum_command("/wiggum") is True

    def test_with_prompt(self):
        from fid_coder.plugins.wiggum.register_callbacks import (
            handle_wiggum_command,
        )

        with (
            patch("fid_coder.plugins.wiggum.state.start"),
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_success"),
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_info"),
        ):
            result = handle_wiggum_command("/wiggum say hello")
            assert result == "say hello"


class TestHandleWiggumStopCommand:
    def test_active(self):
        from fid_coder.plugins.wiggum.register_callbacks import (
            handle_wiggum_stop_command,
        )

        with (
            patch(
                "fid_coder.plugins.wiggum.state.is_active",
                return_value=True,
            ),
            patch("fid_coder.plugins.wiggum.state.stop"),
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_success"),
        ):
            assert handle_wiggum_stop_command("/wiggum_stop") is True

    def test_not_active(self):
        from fid_coder.plugins.wiggum.register_callbacks import (
            handle_wiggum_stop_command,
        )

        with (
            patch(
                "fid_coder.plugins.wiggum.state.is_active",
                return_value=False,
            ),
            patch("fid_coder.plugins.wiggum.register_callbacks.emit_info"),
        ):
            assert handle_wiggum_stop_command("/wiggum_stop") is True


class TestHandleMcpCommand:
    def test_delegates(self):
        from fid_coder.command_line.core_commands import handle_mcp_command

        mock_handler = MagicMock()
        mock_handler.handle_mcp_command.return_value = True
        with patch(
            "fid_coder.command_line.mcp.MCPCommandHandler", return_value=mock_handler
        ):
            assert handle_mcp_command("/mcp") is True
