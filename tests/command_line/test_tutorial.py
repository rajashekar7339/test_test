"""Tests for the /tutorial command flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fid_coder.command_line.core_commands import handle_tutorial_command


def _mock_tutorial_result(mock_executor_class: Any, result: str) -> None:
    mock_future = MagicMock()
    mock_future.result.return_value = result

    mock_executor = MagicMock()
    mock_executor.submit.return_value = mock_future

    mock_executor_class.return_value.__enter__.return_value = mock_executor


def test_tutorial_copilot_flow() -> None:
    """Tutorial triggers GitHub Copilot login."""
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        _mock_tutorial_result(mock_executor_class, "copilot")

        with patch(
            "fid_coder.command_line.onboarding_wizard.reset_onboarding"
        ) as mock_reset:
            with patch(
                "fid_coder.plugins.copilot_auth.register_callbacks._handle_copilot_login"
            ) as mock_login:
                with patch("fid_coder.command_line.core_commands.emit_info"):
                    with patch(
                        "fid_coder.command_line.onboarding_wizard.require_model_setup_if_needed"
                    ):
                        result = handle_tutorial_command("/tutorial")

    assert result is True
    mock_reset.assert_called_once()
    mock_login.assert_called_once_with("/copilot-login")


@pytest.mark.parametrize(
    ("wizard_result", "expected_message"),
    [
        ("completed", "Tutorial complete"),
        ("skipped", "Tutorial skipped"),
    ],
)
def test_tutorial_terminal_paths(wizard_result: str, expected_message: str) -> None:
    """Test tutorial completion and skip paths."""
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_class:
        _mock_tutorial_result(mock_executor_class, wizard_result)

        with patch("fid_coder.command_line.onboarding_wizard.reset_onboarding"):
            with patch("fid_coder.command_line.core_commands.emit_info") as mock_info:
                with patch(
                    "fid_coder.command_line.onboarding_wizard.require_model_setup_if_needed"
                ):
                    result = handle_tutorial_command("/tutorial")

    assert result is True
    assert any(expected_message in str(c) for c in mock_info.call_args_list)
