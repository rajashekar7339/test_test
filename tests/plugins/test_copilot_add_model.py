"""Tests for Copilot-only /add_model (code_puppy-shaped picker)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def menu():
    from fid_coder.plugins.copilot_auth import add_model_menu as mod

    return mod


@pytest.mark.asyncio
async def test_requires_login(menu):
    with (
        patch.object(menu, "load_device_tokens", return_value=[]),
        patch.object(menu, "emit_warning") as warn,
    ):
        assert await menu.interactive_model_picker() is False
        assert "copilot-login" in str(warn.call_args)


@pytest.mark.asyncio
async def test_adds_selected_model(menu):
    token = MagicMock(oauth_token="tok", host="github.com")
    with (
        patch.object(menu, "load_device_tokens", return_value=[token]),
        patch.object(menu, "get_token_for_host", return_value=token),
        patch.object(menu, "get_valid_session_token", return_value="sess"),
        patch.object(
            menu,
            "fetch_copilot_models",
            return_value=["claude-sonnet-4.5", "gpt-4.1"],
        ),
        patch.object(menu, "_registered_ids", return_value=set()),
        patch.object(
            menu,
            "arrow_select_async",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4.5",
        ),
        patch.object(menu, "add_models_to_config", return_value=True) as add,
        patch.object(menu, "emit_info"),
    ):
        assert await menu.interactive_model_picker() is True
        add.assert_called_once_with(["claude-sonnet-4.5"], "github.com")


@pytest.mark.asyncio
async def test_already_registered_returns_false(menu):
    token = MagicMock(oauth_token="tok", host="github.com")
    with (
        patch.object(menu, "load_device_tokens", return_value=[token]),
        patch.object(menu, "get_token_for_host", return_value=token),
        patch.object(menu, "get_valid_session_token", return_value="sess"),
        patch.object(menu, "fetch_copilot_models", return_value=["claude-sonnet-4.5"]),
        patch.object(menu, "_registered_ids", return_value={"claude-sonnet-4.5"}),
        patch.object(
            menu,
            "arrow_select_async",
            new_callable=AsyncMock,
            return_value="claude-sonnet-4.5  ✓ registered",
        ),
        patch.object(menu, "add_models_to_config") as add,
        patch.object(menu, "emit_info"),
    ):
        assert await menu.interactive_model_picker() is False
        add.assert_not_called()


def test_core_command_runs_picker_in_thread():
    from fid_coder.command_line.core_commands import handle_add_model_command

    with (
        patch(
            "fid_coder.plugins.copilot_auth.add_model_menu.interactive_model_picker",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("fid_coder.command_line.core_commands.emit_info") as info,
        patch("fid_coder.tools.command_runner.set_awaiting_user_input"),
    ):
        assert handle_add_model_command("/add_model") is True
        assert "Successfully added" in str(info.call_args)
