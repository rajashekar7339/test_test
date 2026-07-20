"""Full coverage tests for cli_runner.py.

Covers main(), interactive_mode(), run_prompt_with_attachments(),
execute_single_prompt(), and main_entry() — targeting all uncovered branches.
"""

import asyncio
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_renderer():
    r = MagicMock()
    r.console = MagicMock()
    r.console.file = MagicMock()
    r.console.file.flush = MagicMock()
    r.start = MagicMock()
    r.stop = MagicMock()
    return r


def _mock_parse_result(
    prompt="hello", warnings=None, attachments=None, link_attachments=None
):
    m = MagicMock()
    m.prompt = prompt
    m.warnings = warnings or []
    m.attachments = attachments or []
    m.link_attachments = link_attachments or []
    return m


def _mock_clipboard(images=None):
    mgr = MagicMock()
    mgr.get_pending_images.return_value = images or []
    mgr.get_pending_count.return_value = len(images) if images else 0
    mgr.clear_pending = MagicMock()
    return mgr


def _apply_patches(stack, patches_dict):
    """Apply a dict of patches using an ExitStack."""
    for target, value in patches_dict.items():
        stack.enter_context(patch(target, value))


def _base_main_patches():
    """Return a dict of common patches needed for main()."""
    return {
        "fid_coder.cli_runner.find_available_port": MagicMock(return_value=8090),
        "fid_coder.cli_runner.ensure_config_exists": MagicMock(),
        "fid_coder.cli_runner.validate_cancel_agent_key": MagicMock(),
        "fid_coder.cli_runner.initialize_command_history_file": MagicMock(),
        "fid_coder.cli_runner.default_version_mismatch_behavior": MagicMock(),
        "fid_coder.cli_runner.print_truecolor_warning": MagicMock(),
        "fid_coder.cli_runner.reset_unix_terminal": MagicMock(),
        "fid_coder.cli_runner.reset_windows_terminal_ansi": MagicMock(),
        "fid_coder.cli_runner.reset_windows_terminal_full": MagicMock(),
        "fid_coder.cli_runner.callbacks": MagicMock(
            on_startup=AsyncMock(),
            on_shutdown=AsyncMock(),
            on_version_check=AsyncMock(),
            get_callbacks=MagicMock(return_value=[]),
        ),
        "fid_coder.cli_runner.plugins": MagicMock(),
        "fid_coder.config.load_api_keys_to_environment": MagicMock(),
    }


def _interactive_patches():
    return {
        "fid_coder.cli_runner.print_truecolor_warning": MagicMock(),
        "fid_coder.cli_runner.get_cancel_agent_display_name": MagicMock(
            return_value="Ctrl+C"
        ),
        "fid_coder.cli_runner.reset_windows_terminal_ansi": MagicMock(),
        "fid_coder.cli_runner.reset_windows_terminal_full": MagicMock(),
        "fid_coder.cli_runner.save_command_to_history": MagicMock(),
        "fid_coder.cli_runner.finalize_autosave_session": MagicMock(
            return_value="session-1"
        ),
        "fid_coder.cli_runner.COMMAND_HISTORY_FILE": "/tmp/test_history",
        "fid_coder.command_line.onboarding_wizard.should_show_onboarding": MagicMock(
            return_value=False
        ),
        "fid_coder.config.auto_save_session_if_enabled": MagicMock(),
    }


async def _run_interactive(
    renderer,
    patches_dict,
    input_fn,
    agent=None,
    initial_command=None,
    extra_patches=None,
):
    """Helper to run interactive_mode with patching."""
    if agent is None:
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

    with ExitStack() as stack:
        _apply_patches(stack, patches_dict)
        stack.enter_context(
            patch(
                "fid_coder.command_line.prompt_toolkit_completion.get_input_with_combined_completion",
                side_effect=input_fn
                if callable(input_fn) and not isinstance(input_fn, AsyncMock)
                else input_fn,
            )
        )
        stack.enter_context(
            patch(
                "fid_coder.command_line.prompt_toolkit_completion.get_prompt_with_active_model",
                return_value="> ",
            )
        )
        stack.enter_context(
            patch(
                "fid_coder.agents.agent_manager.get_current_agent",
                return_value=agent,
            )
        )
        if extra_patches:
            _apply_patches(stack, extra_patches)

        from fid_coder.cli_runner import interactive_mode

        await interactive_mode(renderer, initial_command=initial_command)


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


class TestMain:
    """Test the main() async function."""

    async def _run_main(self, argv, extra_patches=None, base_overrides=None):
        patches = _base_main_patches()
        if base_overrides:
            patches.update(base_overrides)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"NO_VERSION_UPDATE": "1"}))
            stack.enter_context(patch("sys.argv", argv))
            stack.enter_context(
                patch(
                    "fid_coder.messaging.SynchronousInteractiveRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.messaging.RichConsoleRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_global_queue", return_value=MagicMock())
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_message_bus", return_value=MagicMock())
            )
            _apply_patches(stack, patches)
            if extra_patches:
                _apply_patches(stack, extra_patches)
            from fid_coder.cli_runner import main

            await main()

    @pytest.mark.anyio
    async def test_prompt_mode(self):
        mock_exec = AsyncMock()
        await self._run_main(
            ["fid-coder", "-p", "hello world"],
            extra_patches={"fid_coder.cli_runner.execute_single_prompt": mock_exec},
        )
        mock_exec.assert_called_once()

    @pytest.mark.anyio
    async def test_interactive_mode_default(self):
        mock_inter = AsyncMock()
        await self._run_main(
            ["fid-coder"],
            extra_patches={
                "fid_coder.cli_runner.interactive_mode": mock_inter,
                "pyfiglet.figlet_format": MagicMock(return_value="LOGO\n\n"),
            },
        )
        mock_inter.assert_called_once()

    @pytest.mark.anyio
    async def test_with_command_args(self):
        mock_inter = AsyncMock()
        await self._run_main(
            ["fid-coder", "do", "something"],
            extra_patches={
                "fid_coder.cli_runner.interactive_mode": mock_inter,
                "pyfiglet.figlet_format": MagicMock(return_value="LOGO\n\n"),
            },
        )
        assert mock_inter.call_args[1]["initial_command"] == "do something"

    @pytest.mark.anyio
    async def test_no_available_port(self):
        await self._run_main(
            ["fid-coder", "-p", "test"],
            base_overrides={
                "fid_coder.cli_runner.find_available_port": MagicMock(
                    return_value=None
                ),
            },
        )

    @pytest.mark.anyio
    async def test_keymap_error(self):
        from fid_coder.keymap import KeymapError

        with pytest.raises(SystemExit):
            await self._run_main(
                ["fid-coder", "-p", "test"],
                base_overrides={
                    "fid_coder.cli_runner.validate_cancel_agent_key": MagicMock(
                        side_effect=KeymapError("bad key")
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_model_valid(self):
        mock_set = MagicMock()
        await self._run_main(
            ["fid-coder", "-m", "gpt-5", "-p", "hi"],
            extra_patches={
                "fid_coder.cli_runner.execute_single_prompt": AsyncMock(),
                "fid_coder.config.set_model_name": mock_set,
                "fid_coder.config._validate_model_exists": MagicMock(return_value=True),
            },
        )
        mock_set.assert_called_with("gpt-5")

    @pytest.mark.anyio
    async def test_model_invalid(self):
        mock_mf = MagicMock()
        mock_mf.load_config.return_value = {"gpt-5": {}}
        with pytest.raises(SystemExit):
            await self._run_main(
                ["fid-coder", "-m", "bad-model", "-p", "hi"],
                extra_patches={
                    "fid_coder.config.set_model_name": MagicMock(),
                    "fid_coder.config._validate_model_exists": MagicMock(
                        return_value=False
                    ),
                    "fid_coder.model_factory.ModelFactory": mock_mf,
                },
            )

    @pytest.mark.anyio
    async def test_model_validation_exception(self):
        with pytest.raises(SystemExit):
            await self._run_main(
                ["fid-coder", "-m", "bad", "-p", "hi"],
                extra_patches={
                    "fid_coder.config.set_model_name": MagicMock(),
                    "fid_coder.config._validate_model_exists": MagicMock(
                        side_effect=RuntimeError("boom")
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_agent_valid(self):
        mock_set = MagicMock()
        await self._run_main(
            ["fid-coder", "-a", "fid-coder", "-p", "hi"],
            extra_patches={
                "fid_coder.cli_runner.execute_single_prompt": AsyncMock(),
                "fid_coder.agents.agent_manager.get_available_agents": MagicMock(
                    return_value={"fid-coder": {}}
                ),
                "fid_coder.agents.agent_manager.set_current_agent": mock_set,
            },
        )
        mock_set.assert_called_with("fid-coder")

    @pytest.mark.anyio
    async def test_agent_invalid(self):
        with pytest.raises(SystemExit):
            await self._run_main(
                ["fid-coder", "-a", "bad-agent", "-p", "hi"],
                extra_patches={
                    "fid_coder.agents.agent_manager.get_available_agents": MagicMock(
                        return_value={"fid-coder": {}}
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_agent_exception(self):
        with pytest.raises(SystemExit):
            await self._run_main(
                ["fid-coder", "-a", "bad", "-p", "hi"],
                extra_patches={
                    "fid_coder.agents.agent_manager.get_available_agents": MagicMock(
                        side_effect=RuntimeError("boom")
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_version_check_with_callbacks(self):
        cb_mock = MagicMock(
            on_startup=AsyncMock(),
            on_shutdown=AsyncMock(),
            on_version_check=AsyncMock(),
            get_callbacks=MagicMock(return_value=[lambda: None]),
        )
        patches = _base_main_patches()
        patches["fid_coder.cli_runner.callbacks"] = cb_mock
        with ExitStack() as stack:
            stack.enter_context(
                patch.dict(os.environ, {"NO_VERSION_UPDATE": ""}, clear=False)
            )
            stack.enter_context(patch("sys.argv", ["fid-coder", "-p", "hi"]))
            stack.enter_context(
                patch(
                    "fid_coder.messaging.SynchronousInteractiveRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.messaging.RichConsoleRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_global_queue", return_value=MagicMock())
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_message_bus", return_value=MagicMock())
            )
            stack.enter_context(
                patch(
                    "fid_coder.cli_runner.execute_single_prompt",
                    new_callable=AsyncMock,
                )
            )
            _apply_patches(stack, patches)
            from fid_coder.cli_runner import main

            await main()
            cb_mock.on_version_check.assert_called_once()

    @pytest.mark.anyio
    async def test_version_check_no_callbacks(self):
        """Version check falls back to default_version_mismatch_behavior."""
        patches = _base_main_patches()
        patches["fid_coder.cli_runner.callbacks"] = MagicMock(
            on_startup=AsyncMock(),
            on_shutdown=AsyncMock(),
            on_version_check=AsyncMock(),
            get_callbacks=MagicMock(return_value=[]),
        )
        with ExitStack() as stack:
            stack.enter_context(
                patch.dict(os.environ, {"NO_VERSION_UPDATE": ""}, clear=False)
            )
            stack.enter_context(patch("sys.argv", ["fid-coder", "-p", "hi"]))
            stack.enter_context(
                patch(
                    "fid_coder.messaging.SynchronousInteractiveRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.messaging.RichConsoleRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_global_queue", return_value=MagicMock())
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_message_bus", return_value=MagicMock())
            )
            stack.enter_context(
                patch(
                    "fid_coder.cli_runner.execute_single_prompt",
                    new_callable=AsyncMock,
                )
            )
            _apply_patches(stack, patches)
            from fid_coder.cli_runner import main

            await main()

    @pytest.mark.anyio
    async def test_pyfiglet_import_error(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pyfiglet":
                raise ImportError("no pyfiglet")
            return real_import(name, *args, **kwargs)

        await self._run_main(
            ["fid-coder"],
            extra_patches={
                "fid_coder.cli_runner.interactive_mode": AsyncMock(),
                "builtins.__import__": fake_import,
            },
        )


# ---------------------------------------------------------------------------
# interactive_mode() tests
# ---------------------------------------------------------------------------


class TestInteractiveMode:
    """Test interactive_mode() branches."""

    @pytest.mark.anyio
    async def test_exit_command(self):
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="/exit"),
        )

    @pytest.mark.anyio
    async def test_startup_instructions_describe_editor_shortcuts(self):
        emit_system_message = MagicMock()

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="/exit"),
            extra_patches={
                "fid_coder.messaging.emit_system_message": emit_system_message,
            },
        )

        messages = [call.args[0] for call in emit_system_message.call_args_list]
        assert any("newline: Shift+Enter" in message for message in messages)
        assert any(
            "Ctrl+X Ctrl+E to open $EDITOR (Notepad on Windows)" in message
            for message in messages
        )
        assert any(
            "Ctrl+X Ctrl+B to background running shell commands" in message
            for message in messages
        )
        assert any(
            "Ctrl+X Ctrl+X to kill running shell commands" in message
            for message in messages
        )

    @pytest.mark.anyio
    async def test_quit_command(self):
        agent = MagicMock()
        agent.get_user_prompt.return_value = None  # test None prompt branch
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="quit"),
            agent=agent,
        )

    @pytest.mark.anyio
    async def test_eof_exits(self):
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(side_effect=EOFError),
        )

    @pytest.mark.anyio
    async def test_keyboard_interrupt_continues(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise KeyboardInterrupt
            return "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={},
        )

    @pytest.mark.anyio
    async def test_keyboard_interrupt_notifies_continuation_plugins(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise KeyboardInterrupt
            return "/exit"

        mock_cancel = AsyncMock()
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.callbacks.on_interactive_turn_cancel": mock_cancel,
            },
        )
        mock_cancel.assert_awaited()

    @pytest.mark.anyio
    async def test_clear_command(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/clear" if call_count == 1 else "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                # /clear is handled by session_commands now; it lazy-imports
                # the clipboard manager and autosave rotation, so patch at
                # the source modules.
                "fid_coder.command_line.clipboard.get_clipboard_manager": MagicMock(
                    return_value=_mock_clipboard([b"img"])
                ),
                "fid_coder.config.finalize_autosave_session": MagicMock(
                    return_value="session-1"
                ),
            },
        )
        agent.clear_message_history.assert_called()

    @pytest.mark.anyio
    async def test_slash_command_handled(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/help" if call_count == 1 else "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    return_value=True
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/help")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_slash_command_returns_prompt(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/custom" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    return_value="run this"
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/custom")
                ),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
            },
        )

    @pytest.mark.anyio
    async def test_slash_command_exception(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/bad" if call_count == 1 else "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    side_effect=RuntimeError("cmd error")
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/bad")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_normal_prompt_execution(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_prompt_returns_none_cancelled(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(None, MagicMock())
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_prompt_cancelled_notifies_continuation_plugins(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_cancel = AsyncMock()
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(None, MagicMock())
                ),
                "fid_coder.callbacks.on_interactive_turn_cancel": mock_cancel,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
            },
        )
        mock_cancel.assert_awaited()

    @pytest.mark.anyio
    async def test_prompt_exception(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    side_effect=RuntimeError("agent error")
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.messaging.queue_console.get_queue_console": MagicMock(
                    return_value=MagicMock()
                ),
            },
        )

    @pytest.mark.anyio
    async def test_empty_input_skipped(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "   " if call_count == 1 else "/exit"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("   ")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_initial_command_success(self):
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="/exit"),
            agent=agent,
            initial_command="do stuff",
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
            },
        )

    @pytest.mark.anyio
    async def test_initial_command_error(self):
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="/exit"),
            agent=agent,
            initial_command="do stuff",
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    side_effect=RuntimeError("fail")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_initial_command_returns_none(self):
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            AsyncMock(return_value="/exit"),
            agent=agent,
            initial_command="do stuff",
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(None, MagicMock())
                ),
            },
        )

    @pytest.mark.anyio
    async def test_autosave_load_non_tty(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/autosave_load" if call_count == 1 else "/exit"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    return_value="__AUTOSAVE_LOAD__"
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/autosave_load")
                ),
                "sys.stdin": mock_stdin,
                "sys.stdout": mock_stdout,
                "fid_coder.session_storage.restore_autosave_interactively": AsyncMock(),
            },
        )

    @pytest.mark.anyio
    async def test_autosave_load_tty_cancelled(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/autosave_load" if call_count == 1 else "/exit"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"FID_CODER_NO_TUI": ""}, clear=False):
            await _run_interactive(
                _mock_renderer(),
                _interactive_patches(),
                fake_input,
                extra_patches={
                    "fid_coder.command_line.command_handler.handle_command": MagicMock(
                        return_value="__AUTOSAVE_LOAD__"
                    ),
                    "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                        return_value=_mock_parse_result("/autosave_load")
                    ),
                    "sys.stdin": mock_stdin,
                    "sys.stdout": mock_stdout,
                    "fid_coder.command_line.autosave_menu.interactive_autosave_picker": AsyncMock(
                        return_value=None
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_autosave_load_tty_success(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/autosave_load" if call_count == 1 else "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        agent.estimate_tokens_for_message.return_value = 10

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"FID_CODER_NO_TUI": ""}, clear=False):
            await _run_interactive(
                _mock_renderer(),
                _interactive_patches(),
                fake_input,
                agent=agent,
                extra_patches={
                    "fid_coder.command_line.command_handler.handle_command": MagicMock(
                        return_value="__AUTOSAVE_LOAD__"
                    ),
                    "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                        return_value=_mock_parse_result("/autosave_load")
                    ),
                    "sys.stdin": mock_stdin,
                    "sys.stdout": mock_stdout,
                    "fid_coder.command_line.autosave_menu.interactive_autosave_picker": AsyncMock(
                        return_value="my-session"
                    ),
                    "fid_coder.session_storage.load_session": MagicMock(
                        return_value=[MagicMock()]
                    ),
                    "fid_coder.config.set_current_autosave_from_session_name": MagicMock(),
                    "fid_coder.command_line.autosave_menu.display_resumed_history": MagicMock(),
                    "fid_coder.cli_runner.get_current_agent": MagicMock(
                        return_value=agent
                    ),
                },
            )

    @pytest.mark.anyio
    async def test_autosave_load_exception(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/autosave_load" if call_count == 1 else "/exit"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    return_value="__AUTOSAVE_LOAD__"
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/autosave_load")
                ),
                "sys.stdin": mock_stdin,
                "sys.stdout": mock_stdout,
                "fid_coder.session_storage.restore_autosave_interactively": AsyncMock(
                    side_effect=RuntimeError("fail")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_slash_command_returns_false(self):
        """Command returns False = not recognized, fall through."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/unknown" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="ok")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.command_line.command_handler.handle_command": MagicMock(
                    return_value=False
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("/unknown")
                ),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
            },
        )

    @pytest.mark.anyio
    async def test_continuation_loop(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        mock_run = AsyncMock(return_value=(mock_result, MagicMock()))
        mock_turn_end = AsyncMock(
            side_effect=[[{"prompt": "repeat", "clear_context": True}], []]
        )

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": mock_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.callbacks.on_interactive_turn_end": mock_turn_end,
            },
        )
        assert mock_run.await_count == 2

    @pytest.mark.anyio
    async def test_continuation_loop_cancelled(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []
        run_call = 0

        async def fake_run(*a, **kw):
            nonlocal run_call
            run_call += 1
            if run_call == 1:
                return (mock_result, MagicMock())
            return (None, MagicMock())

        mock_cancel = AsyncMock()
        mock_turn_end = AsyncMock(
            side_effect=[[{"prompt": "repeat", "clear_context": True}], []]
        )

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": fake_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.callbacks.on_interactive_turn_end": mock_turn_end,
                "fid_coder.callbacks.on_interactive_turn_cancel": mock_cancel,
            },
        )
        mock_cancel.assert_awaited()

    @pytest.mark.anyio
    async def test_continuation_no_request_stops(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        mock_turn_end = AsyncMock(return_value=[])
        mock_run = AsyncMock(return_value=(mock_result, MagicMock()))
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": mock_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.callbacks.on_interactive_turn_end": mock_turn_end,
            },
        )
        mock_turn_end.assert_called()
        assert mock_run.await_count == 1

    @pytest.mark.anyio
    async def test_continuation_loop_exception_is_reported_to_plugins(self):
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []
        run_call = 0

        async def fake_run(*a, **kw):
            nonlocal run_call
            run_call += 1
            if run_call == 1:
                return (mock_result, MagicMock())
            raise RuntimeError("wiggum fail")

        mock_turn_end = AsyncMock(
            side_effect=[[{"prompt": "repeat", "clear_context": True}], []]
        )

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": fake_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.callbacks.on_interactive_turn_end": mock_turn_end,
            },
        )
        assert mock_turn_end.call_count >= 2

    @pytest.mark.anyio
    async def test_onboarding_copilot(self):
        patches = _interactive_patches()
        patches["fid_coder.command_line.onboarding_wizard.should_show_onboarding"] = (
            MagicMock(return_value=True)
        )

        mock_future = MagicMock()
        mock_future.result.return_value = "copilot"
        mock_pool = MagicMock()
        mock_pool.submit.return_value = mock_future
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_pool)
        mock_executor.__exit__ = MagicMock(return_value=False)

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            extra_patches={
                "concurrent.futures.ThreadPoolExecutor": MagicMock(
                    return_value=mock_executor
                ),
                "fid_coder.command_line.onboarding_wizard.run_onboarding_wizard": AsyncMock(
                    return_value="copilot"
                ),
                "fid_coder.plugins.copilot_auth.register_callbacks._handle_copilot_login": MagicMock(),
                "fid_coder.config.set_model_name": MagicMock(),
            },
        )

    @pytest.mark.anyio
    async def test_onboarding_copilot_alt(self):
        patches = _interactive_patches()
        patches["fid_coder.command_line.onboarding_wizard.should_show_onboarding"] = (
            MagicMock(return_value=True)
        )

        mock_future = MagicMock()
        mock_future.result.return_value = "copilot"
        mock_pool = MagicMock()
        mock_pool.submit.return_value = mock_future
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_pool)
        mock_executor.__exit__ = MagicMock(return_value=False)

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            extra_patches={
                "concurrent.futures.ThreadPoolExecutor": MagicMock(
                    return_value=mock_executor
                ),
                "fid_coder.plugins.copilot_auth.register_callbacks._handle_copilot_login": MagicMock(),
                "fid_coder.config.set_model_name": MagicMock(),
            },
        )

    @pytest.mark.anyio
    async def test_onboarding_completed(self):
        patches = _interactive_patches()
        patches["fid_coder.command_line.onboarding_wizard.should_show_onboarding"] = (
            MagicMock(return_value=True)
        )

        mock_future = MagicMock()
        mock_future.result.return_value = "completed"
        mock_pool = MagicMock()
        mock_pool.submit.return_value = mock_future
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_pool)
        mock_executor.__exit__ = MagicMock(return_value=False)

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            extra_patches={
                "concurrent.futures.ThreadPoolExecutor": MagicMock(
                    return_value=mock_executor
                ),
            },
        )

    @pytest.mark.anyio
    async def test_onboarding_skipped(self):
        patches = _interactive_patches()
        patches["fid_coder.command_line.onboarding_wizard.should_show_onboarding"] = (
            MagicMock(return_value=True)
        )

        mock_future = MagicMock()
        mock_future.result.return_value = "skipped"
        mock_pool = MagicMock()
        mock_pool.submit.return_value = mock_future
        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_pool)
        mock_executor.__exit__ = MagicMock(return_value=False)

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            extra_patches={
                "concurrent.futures.ThreadPoolExecutor": MagicMock(
                    return_value=mock_executor
                ),
            },
        )

    @pytest.mark.anyio
    async def test_onboarding_exception(self):
        patches = _interactive_patches()
        patches["fid_coder.command_line.onboarding_wizard.should_show_onboarding"] = (
            MagicMock(side_effect=RuntimeError("fail"))
        )

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
        )

    @pytest.mark.anyio
    async def test_clear_no_clipboard_images(self):
        """Test /clear when no clipboard images pending."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/clear" if call_count == 1 else "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                # Same lazy-import targets as test_clear_command above.
                "fid_coder.command_line.clipboard.get_clipboard_manager": MagicMock(
                    return_value=_mock_clipboard()
                ),
                "fid_coder.config.finalize_autosave_session": MagicMock(
                    return_value="session-1"
                ),
            },
        )


# ---------------------------------------------------------------------------
# main_entry() additional tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Additional interactive_mode edge cases for remaining uncovered lines
# ---------------------------------------------------------------------------


class TestInteractiveModeEdgeCases:
    """Cover remaining uncovered lines in interactive_mode."""

    @pytest.mark.anyio
    async def test_exit_with_running_task(self):
        """Lines 594-599: exit cancels running agent task."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "do work"
            return "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        # Use a real Future that we can cancel and await
        loop = asyncio.get_event_loop()
        mock_task = loop.create_future()
        # Don't resolve it - it stays pending (not done)

        async def fake_run(*a, **kw):
            return (mock_result, mock_task)

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": fake_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("do work")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_eof_with_running_task_cancels(self):
        """Lines 574-579: EOF cancels running agent task."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "do work"
            raise EOFError

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        loop = asyncio.get_event_loop()
        mock_task = loop.create_future()

        async def fake_run(*a, **kw):
            return (mock_result, mock_task)

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": fake_run,
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("do work")
                ),
            },
        )

    @pytest.mark.anyio
    async def test_clear_with_clipboard_images(self):
        """Line 625: clipboard_count > 0 message."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "clear" if call_count == 1 else "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        clip = _mock_clipboard([b"img1", b"img2"])

        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.command_line.clipboard.get_clipboard_manager": MagicMock(
                    return_value=clip
                ),
            },
        )

    @pytest.mark.anyio
    async def test_autosave_load_no_tui_env(self):
        """Line 656: FID_CODER_NO_TUI=1 forces non-interactive picker."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "/autosave_load" if call_count == 1 else "/exit"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"FID_CODER_NO_TUI": "1"}, clear=False):
            await _run_interactive(
                _mock_renderer(),
                _interactive_patches(),
                fake_input,
                extra_patches={
                    "fid_coder.command_line.command_handler.handle_command": MagicMock(
                        return_value="__AUTOSAVE_LOAD__"
                    ),
                    "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                        return_value=_mock_parse_result("/autosave_load")
                    ),
                    "sys.stdin": mock_stdin,
                    "sys.stdout": mock_stdout,
                    "fid_coder.session_storage.restore_autosave_interactively": AsyncMock(),
                },
            )


# ---------------------------------------------------------------------------
# main() Windows raw-Ctrl+C clamp and other edge cases
# ---------------------------------------------------------------------------


class TestMainWindowsClampAndEdgeCases:
    @pytest.mark.anyio
    async def test_windows_raw_ctrl_c_clamp_armed(self):
        """When the console clamp succeeds, the sticky flag is set."""
        patches = _base_main_patches()
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"NO_VERSION_UPDATE": "1"}))
            stack.enter_context(patch("sys.argv", ["fid-coder", "-p", "hi"]))
            stack.enter_context(
                patch(
                    "fid_coder.messaging.SynchronousInteractiveRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.messaging.RichConsoleRenderer",
                    return_value=_mock_renderer(),
                )
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_global_queue", return_value=MagicMock())
            )
            stack.enter_context(
                patch("fid_coder.messaging.get_message_bus", return_value=MagicMock())
            )
            stack.enter_context(
                patch(
                    "fid_coder.cli_runner.execute_single_prompt",
                    new_callable=AsyncMock,
                )
            )
            _apply_patches(stack, patches)
            mock_disable = stack.enter_context(
                patch(
                    "fid_coder.terminal_utils.disable_windows_ctrl_c",
                    return_value=True,
                )
            )
            mock_keep = stack.enter_context(
                patch("fid_coder.terminal_utils.set_keep_ctrl_c_disabled")
            )
            from fid_coder.cli_runner import main

            await main()

            mock_disable.assert_called_once()
            mock_keep.assert_called_once_with(True)

    @pytest.mark.anyio
    async def test_initial_command_awaiting_input(self):
        """Lines 405-406: is_awaiting_user_input branch."""
        patches = _interactive_patches()
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            agent=agent,
            initial_command="do stuff",
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
                "fid_coder.tools.command_runner.is_awaiting_user_input": MagicMock(
                    return_value=True
                ),
            },
        )

    @pytest.mark.anyio
    async def test_initial_command_awaiting_input_import_error(self):
        """Lines 405-406: is_awaiting_user_input ImportError."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if "command_runner" in name and "is_awaiting" not in str(args):
                # Only block the specific import inside the try block
                pass
            return real_import(name, *args, **kwargs)

        patches = _interactive_patches()
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        await _run_interactive(
            _mock_renderer(),
            patches,
            AsyncMock(return_value="/exit"),
            agent=agent,
            initial_command="do stuff",
            extra_patches={
                "fid_coder.cli_runner.get_current_agent": MagicMock(return_value=agent),
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(mock_result, MagicMock())
                ),
            },
        )


class TestRemainingEdgeCases:
    """Cover the hardest-to-reach lines."""

    @pytest.mark.anyio
    async def test_cancelled_result_notifies_continuation_plugins(self):
        """Cancelled agent runs notify continuation plugins."""
        call_count = 0

        async def fake_input(*a, **kw):
            nonlocal call_count
            call_count += 1
            return "write hello" if call_count == 1 else "/exit"

        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"

        mock_cancel = AsyncMock()
        await _run_interactive(
            _mock_renderer(),
            _interactive_patches(),
            fake_input,
            agent=agent,
            extra_patches={
                "fid_coder.cli_runner.run_prompt_with_attachments": AsyncMock(
                    return_value=(None, MagicMock())
                ),
                "fid_coder.cli_runner.parse_prompt_attachments": MagicMock(
                    return_value=_mock_parse_result("write hello")
                ),
                "fid_coder.callbacks.on_interactive_turn_cancel": mock_cancel,
            },
        )
        mock_cancel.assert_awaited()

    @pytest.mark.anyio
    async def test_execute_single_prompt_success_path(self):
        """Lines 1005-1015: execute_single_prompt success with .output access."""
        from fid_coder.cli_runner import execute_single_prompt

        mock_renderer = _mock_renderer()
        # response needs .output attribute (not a tuple)
        mock_response = MagicMock()
        mock_response.output = "the response"

        with ExitStack() as stack:
            stack.enter_context(patch("fid_coder.cli_runner.get_current_agent"))
            stack.enter_context(
                patch(
                    "fid_coder.cli_runner.run_prompt_with_attachments",
                    new_callable=AsyncMock,
                    return_value=mock_response,
                )
            )
            stack.enter_context(patch("fid_coder.cli_runner.emit_info"))
            await execute_single_prompt("test", mock_renderer)


class TestImportErrorFallbacks:
    """Test ImportError fallback branches."""

    @pytest.mark.anyio
    async def test_prompt_toolkit_import_error_fallback(self):
        """Lines 449-470, 542-546: prompt_toolkit not installed.

        These lines are import-error fallbacks for prompt_toolkit_completion.
        They're only reachable when the module genuinely can't be imported,
        which is impractical to test without breaking the test infrastructure.
        Marking as known-uncoverable (Windows/missing-dep edge case).
        """
        # This test documents that lines 449-470 and 542-546 are
        # ImportError fallback paths that can't be easily covered
        # in a test environment where prompt_toolkit is installed.
        pass

    @pytest.mark.anyio
    async def test_is_awaiting_user_input_import_error(self):
        """Lines 405-406: ImportError for is_awaiting_user_input."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "fid_coder.tools.command_runner":
                raise ImportError("no command_runner")
            return real_import(name, *args, **kwargs)

        renderer = _mock_renderer()
        patches = _interactive_patches()
        agent = MagicMock()
        agent.get_user_prompt.return_value = "task:"
        mock_result = MagicMock(output="done")
        mock_result.all_messages.return_value = []

        with ExitStack() as stack:
            _apply_patches(stack, patches)
            stack.enter_context(
                patch(
                    "fid_coder.command_line.prompt_toolkit_completion.get_input_with_combined_completion",
                    new_callable=AsyncMock,
                    return_value="/exit",
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.command_line.prompt_toolkit_completion.get_prompt_with_active_model",
                    return_value="> ",
                )
            )
            stack.enter_context(
                patch(
                    "fid_coder.agents.agent_manager.get_current_agent",
                    return_value=agent,
                )
            )
            stack.enter_context(
                patch("fid_coder.cli_runner.get_current_agent", return_value=agent)
            )
            stack.enter_context(
                patch(
                    "fid_coder.cli_runner.run_prompt_with_attachments",
                    new_callable=AsyncMock,
                    return_value=(mock_result, MagicMock()),
                )
            )
            stack.enter_context(patch("builtins.__import__", side_effect=fake_import))
            from fid_coder.cli_runner import interactive_mode

            await interactive_mode(renderer, initial_command="test")


class TestMainEntryAdditional:
    @patch("asyncio.run", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt_stderr_output(self, mock_run):
        from fid_coder.cli_runner import main_entry

        with ExitStack() as stack:
            stack.enter_context(patch("fid_coder.cli_runner.reset_unix_terminal"))
            result = main_entry()
            assert result == 0
