"""Full coverage tests for fid_coder/command_line/config_commands.py."""

from unittest.mock import MagicMock, patch


class TestGetCommandsHelp:
    def test_lazy_import(self):
        from fid_coder.command_line.config_commands import get_commands_help

        with patch(
            "fid_coder.command_line.command_handler.get_commands_help",
            return_value="help text",
        ):
            assert get_commands_help() == "help text"


class TestHandleShowCommand:
    def _show_patches(self, effective_temp=0.7, global_temp=0.7, yolo=True):
        """Return a context manager patching all lazy imports in handle_show_command."""
        mock_agent = MagicMock()
        mock_agent.display_name = "Test Agent"
        return [
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
            patch(
                "fid_coder.command_line.model_picker_completion.get_active_model",
                return_value="gpt-5",
            ),
            patch("fid_coder.config.get_fid_name", return_value="Pup"),
            patch("fid_coder.config.get_owner_name", return_value="Owner"),
            patch("fid_coder.config.get_yolo_mode", return_value=yolo),
            patch("fid_coder.config.get_auto_save_session", return_value=True),
            patch("fid_coder.config.get_protected_token_count", return_value=50000),
            patch("fid_coder.config.get_compaction_threshold", return_value=0.85),
            patch(
                "fid_coder.config.get_compaction_strategy", return_value="truncation"
            ),
            patch("fid_coder.config.get_temperature", return_value=global_temp),
            patch(
                "fid_coder.config.get_effective_temperature",
                return_value=effective_temp,
            ),
            patch("fid_coder.config.get_default_agent", return_value="fid-coder"),
            patch("fid_coder.config.get_resume_message_count", return_value=50),
            patch(
                "fid_coder.config.get_openai_reasoning_effort", return_value="medium"
            ),
            patch("fid_coder.config.get_openai_verbosity", return_value="medium"),
            patch(
                "fid_coder.keymap.get_cancel_agent_display_name", return_value="ctrl+c"
            ),
            patch("fid_coder.messaging.emit_info"),
        ]

    def test_show_command(self):
        from fid_coder.command_line.config_commands import handle_show_command

        patches = self._show_patches()
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
            patches[8],
            patches[9],
            patches[10],
            patches[11],
            patches[12],
            patches[13],
            patches[14],
            patches[15],
            patches[16],
        ):
            assert handle_show_command("/show") is True

    def test_show_effective_temp_none(self):
        from fid_coder.command_line.config_commands import handle_show_command

        patches = self._show_patches(effective_temp=None, global_temp=None)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
            patches[8],
            patches[9],
            patches[10],
            patches[11],
            patches[12],
            patches[13],
            patches[14],
            patches[15],
            patches[16],
        ):
            assert handle_show_command("/show") is True


class TestHandleSetCommand:
    def test_no_args_launches_menu(self):
        from fid_coder.command_line.config_commands import handle_set_command

        with patch(
            "fid_coder.command_line.set_menu.interactive_set_picker",
            return_value=None,
        ):
            assert handle_set_command("/set") is True

    def test_equals_syntax(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set key=value") is True

    def test_space_syntax(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set key value") is True

    def test_key_only(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set key") is True

    def test_enable_dbos(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set enable_dbos true") is True

    def test_cancel_agent_key_valid(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.keymap.VALID_CANCEL_KEYS", {"ctrl+c", "ctrl+k", "ctrl+q"}),
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set cancel_agent_key ctrl+c") is True

    def test_cancel_agent_key_invalid(self):
        from fid_coder.command_line.config_commands import handle_set_command

        with (
            patch("fid_coder.keymap.VALID_CANCEL_KEYS", {"ctrl+c", "ctrl+k", "ctrl+q"}),
            patch("fid_coder.messaging.emit_error") as err,
        ):
            assert handle_set_command("/set cancel_agent_key bad_key") is True
            err.assert_called_once()

    def test_agent_reload_failure(self):
        from fid_coder.command_line.config_commands import handle_set_command

        mock_agent = MagicMock()
        mock_agent.reload_code_generation_agent.side_effect = Exception("boom")
        with (
            patch("fid_coder.config.set_config_value"),
            patch("fid_coder.messaging.emit_success"),
            patch("fid_coder.messaging.emit_info"),
            patch("fid_coder.messaging.emit_warning") as warn,
            patch("fid_coder.agents.get_current_agent", return_value=mock_agent),
        ):
            assert handle_set_command("/set key value") is True
            warn.assert_called_once()


class TestHandleDiffCommand:
    def _pool_mock(self, result):
        mock_pool = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = result
        mock_pool.__enter__ = MagicMock(return_value=mock_pool)
        mock_pool.__exit__ = MagicMock(return_value=False)
        mock_pool.submit.return_value = mock_future
        return mock_pool

    def test_with_result(self):
        from fid_coder.command_line.config_commands import handle_diff_command

        pool = self._pool_mock({"add_color": "green", "del_color": "red"})
        with (
            patch("concurrent.futures.ThreadPoolExecutor", return_value=pool),
            patch("fid_coder.config.set_diff_addition_color"),
            patch("fid_coder.config.set_diff_deletion_color"),
        ):
            assert handle_diff_command("/diff") is True

    def test_no_result(self):
        from fid_coder.command_line.config_commands import handle_diff_command

        pool = self._pool_mock(None)
        with patch("concurrent.futures.ThreadPoolExecutor", return_value=pool):
            assert handle_diff_command("/diff") is True

    def test_error_applying(self):
        from fid_coder.command_line.config_commands import handle_diff_command

        pool = self._pool_mock({"add_color": "g", "del_color": "r"})
        with (
            patch("concurrent.futures.ThreadPoolExecutor", return_value=pool),
            patch(
                "fid_coder.config.set_diff_addition_color",
                side_effect=Exception("fail"),
            ),
            patch("fid_coder.messaging.emit_error"),
        ):
            assert handle_diff_command("/diff") is True


class TestHandleColorsCommand:
    def test_colors_command_removed(self):
        from fid_coder.command_line import config_commands  # noqa: F401 — register cmds
        from fid_coder.command_line.command_registry import get_command

        assert get_command("colors") is None


class TestShowColorOptions:
    def test_additions(self):
        from fid_coder.command_line.config_commands import _show_color_options

        with patch("fid_coder.messaging.emit_info"):
            _show_color_options("additions")

    def test_deletions(self):
        from fid_coder.command_line.config_commands import _show_color_options

        with patch("fid_coder.messaging.emit_info"):
            _show_color_options("deletions")

    def test_other(self):
        from fid_coder.command_line.config_commands import _show_color_options

        with patch("fid_coder.messaging.emit_info"):
            _show_color_options("other")
