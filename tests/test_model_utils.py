"""Tests for the model_utils module."""

import pytest

from fid_coder.callbacks import (
    clear_callbacks,
    get_callbacks,
    register_callback,
    unregister_callback,
)
from fid_coder.model_utils import (
    PreparedPrompt,
    get_default_extended_thinking,
    get_thinking_tags,
    prepare_prompt_for_model,
    should_use_anthropic_thinking_summary,
    supports_glm_reasoning_effort,
)


@pytest.fixture(autouse=True)
def _isolate_prompt_callbacks():
    """Guarantee test isolation for prompt-related callback phases."""
    saved = {
        phase: list(get_callbacks(phase))
        for phase in ("prepare_model_prompt", "get_model_system_prompt")
    }
    clear_callbacks("prepare_model_prompt")
    clear_callbacks("get_model_system_prompt")
    yield
    clear_callbacks("prepare_model_prompt")
    clear_callbacks("get_model_system_prompt")
    for phase, callbacks in saved.items():
        for cb in callbacks:
            register_callback(phase, cb)


class TestPreparePromptForModel:
    """Tests for prepare_prompt_for_model."""

    def test_non_claude_code_keeps_original_instructions(self):
        """Non-claude-code models should keep original instructions."""
        result = prepare_prompt_for_model(
            "gpt-4", "You are a helpful assistant.", "Hello world"
        )

        assert result.instructions == "You are a helpful assistant."
        assert result.is_claude_code is False

    def test_non_claude_code_keeps_original_prompt(self):
        """Non-claude-code models should keep original user prompt."""
        result = prepare_prompt_for_model(
            "gpt-4", "You are a helpful assistant.", "Hello world"
        )

        assert result.user_prompt == "Hello world"

    def test_returns_prepared_prompt_dataclass(self):
        """Function should return a PreparedPrompt dataclass."""
        result = prepare_prompt_for_model("gpt-4", "System prompt", "User prompt")

        assert isinstance(result, PreparedPrompt)
        assert hasattr(result, "instructions")
        assert hasattr(result, "user_prompt")
        assert hasattr(result, "is_claude_code")

    def test_augmenter_callback_mutations_are_threaded_forward(self):
        """Regression: augmenter plugins returning ``handled=False`` with
        mutated ``instructions`` must have those mutations preserved in the
        returned PreparedPrompt. agent_skills relies on this contract to
        inject the available-skills block into the system prompt.
        """

        def _augmenter(model_name, default_system_prompt, user_prompt):
            return {
                "instructions": f"{default_system_prompt}\n\n## Available Skills\n- foo: bar",
                "user_prompt": user_prompt,
                "handled": False,
            }

        register_callback("get_model_system_prompt", _augmenter)
        try:
            result = prepare_prompt_for_model(
                "gpt-4", "You are a helpful assistant.", "Hello"
            )
        finally:
            # Belt + suspenders — the autouse fixture also restores state.
            unregister_callback("get_model_system_prompt", _augmenter)

        assert "## Available Skills" in result.instructions
        assert "- foo: bar" in result.instructions
        assert result.user_prompt == "Hello"
        assert result.is_claude_code is False

    def test_handled_true_short_circuits_remaining_augmenters(self):
        """A ``handled=True`` result must win outright — later augmenters in
        the chain shouldn't get a chance to mutate the prompt.
        """
        calls: list[str] = []

        def _taker(model_name, default_system_prompt, user_prompt):
            calls.append("taker")
            return {
                "instructions": "TAKEN OVER",
                "user_prompt": user_prompt,
                "handled": True,
            }

        def _augmenter(model_name, default_system_prompt, user_prompt):
            calls.append("augmenter")
            return {
                "instructions": f"{default_system_prompt}\nAUGMENTED",
                "user_prompt": user_prompt,
                "handled": False,
            }

        # Register taker first so it appears first in the dispatch order.
        register_callback("get_model_system_prompt", _taker)
        register_callback("get_model_system_prompt", _augmenter)
        try:
            result = prepare_prompt_for_model("gpt-4", "orig", "hello")
        finally:
            unregister_callback("get_model_system_prompt", _taker)
            unregister_callback("get_model_system_prompt", _augmenter)

        assert result.instructions == "TAKEN OVER"
        # Both callbacks still fire (the dispatcher collects all results),
        # but only the taker's output is honored.
        assert "taker" in calls


class TestPreparedPromptDataclass:
    """Tests for the PreparedPrompt dataclass."""

    def test_dataclass_creation(self):
        """PreparedPrompt should be creatable with all fields."""
        prompt = PreparedPrompt(
            instructions="test instructions",
            user_prompt="test user prompt",
            is_claude_code=True,
        )

        assert prompt.instructions == "test instructions"
        assert prompt.user_prompt == "test user prompt"
        assert prompt.is_claude_code is True

    def test_dataclass_equality(self):
        """Two PreparedPrompts with same values should be equal."""
        prompt1 = PreparedPrompt(
            instructions="test", user_prompt="hello", is_claude_code=False
        )
        prompt2 = PreparedPrompt(
            instructions="test", user_prompt="hello", is_claude_code=False
        )

        assert prompt1 == prompt2


class TestGetDefaultExtendedThinking:
    """Tests for get_default_extended_thinking."""

    def test_opus_4_6_returns_adaptive(self):
        assert get_default_extended_thinking("claude-opus-4-6") == "adaptive"

    def test_4_6_opus_returns_adaptive(self):
        assert get_default_extended_thinking("claude-4-6-opus") == "adaptive"

    def test_case_insensitive(self):
        assert get_default_extended_thinking("Claude-Opus-4-6") == "adaptive"
        assert get_default_extended_thinking("CLAUDE-4-6-OPUS") == "adaptive"

    def test_non_opus_46_returns_enabled(self):
        assert get_default_extended_thinking("claude-sonnet-4-20250514") == "enabled"
        assert get_default_extended_thinking("claude-opus-4-5") == "enabled"
        assert get_default_extended_thinking("claude-4-5-opus") == "enabled"

    def test_non_anthropic_returns_enabled(self):
        assert get_default_extended_thinking("gpt-4o") == "enabled"
        assert get_default_extended_thinking("gemini-2.5-pro") == "enabled"

    def test_substring_match_in_longer_name(self):
        assert get_default_extended_thinking("anthropic-opus-4-6-preview") == "adaptive"
        assert get_default_extended_thinking("claude-4-6-opus-20250701") == "adaptive"

    def test_sonnet_5_returns_adaptive(self):
        # Sonnet 5 defaults to adaptive thinking just like Opus; classic
        # "enabled" thinking is deprecated for it.
        assert get_default_extended_thinking("claude-sonnet-5") == "adaptive"
        assert (
            get_default_extended_thinking("claude-code-claude-sonnet-5") == "adaptive"
        )
        assert get_default_extended_thinking("Claude-Sonnet-5") == "adaptive"
        # Older single-digit sonnet must stay on enabled.
        assert get_default_extended_thinking("claude-sonnet-4-20250514") == "enabled"


class TestShouldUseAnthropicThinkingSummary:
    """Tests for should_use_anthropic_thinking_summary."""

    def test_opus_4_7_models_return_true(self):
        assert should_use_anthropic_thinking_summary("claude-opus-4-7") is True
        assert should_use_anthropic_thinking_summary("Claude-Opus-4-7-Latest") is True
        assert should_use_anthropic_thinking_summary("claude-4-7-opus-20250701") is True

    def test_sonnet_5_models_return_true(self):
        assert should_use_anthropic_thinking_summary("claude-sonnet-5") is True
        assert (
            should_use_anthropic_thinking_summary("claude-code-claude-sonnet-5") is True
        )

    def test_other_models_return_false(self):
        assert should_use_anthropic_thinking_summary("claude-opus-4-6") is False
        assert should_use_anthropic_thinking_summary("claude-sonnet-4") is False
        assert should_use_anthropic_thinking_summary("claude-sonnet-4-6") is False
        assert should_use_anthropic_thinking_summary("gpt-5") is False


class TestGetThinkingTags:
    """Tests for the reasoning-tag override helper.

    The <mm:think> quirk is lilac's PROXY mangling MiniMax's output, not
    something MiniMax itself does -- every other MiniMax deployment (direct,
    other providers) must keep the standard <think>/</think> tags.
    """

    def test_minimax_via_lilac_gets_mm_think_tags(self):
        config = {"provider": "lilac", "name": "minimaxai/minimax-m3"}
        assert get_thinking_tags("lilac-minimaxai-minimax-m3", config) == (
            "<mm:think>",
            "</mm:think>",
        )

    def test_minimax_via_lilac_detected_via_alias_name_too(self):
        # Even without a "name" override, the alias itself mentions minimax.
        config = {"provider": "lilac"}
        assert get_thinking_tags("lilac-minimaxai-minimax-m3", config) == (
            "<mm:think>",
            "</mm:think>",
        )

    def test_minimax_via_other_provider_keeps_default_tags(self):
        # Same model, hosted directly / via a different provider -> no mangling,
        # so we must NOT override its native <think> tags.
        config = {"name": "sparkarena/Minimax-M3-v0-NVFP4"}
        assert get_thinking_tags("boodleton-minimax-m3-nvfp4", config) is None
        assert get_thinking_tags("minimaxai-minimax-m3") is None

    def test_non_minimax_lilac_model_keeps_default_tags(self):
        config = {"provider": "lilac", "name": "zai-org/glm-5.2"}
        assert get_thinking_tags("lilac-zai-org-glm-5.2", config) is None
        assert get_thinking_tags("gpt-5") is None

    def test_explicit_config_override_wins_over_lilac_minimax_default(self):
        config = {
            "provider": "lilac",
            "name": "minimaxai/minimax-m3",
            "thinking_tags": ["<r>", "</r>"],
        }
        assert get_thinking_tags("lilac-minimaxai-minimax-m3", config) == (
            "<r>",
            "</r>",
        )

    def test_explicit_config_override_works_for_arbitrary_models(self):
        config = {"thinking_tags": ["<reasoning>", "</reasoning>"]}
        assert get_thinking_tags("some-quirky-model", config) == (
            "<reasoning>",
            "</reasoning>",
        )
        assert supports_glm_reasoning_effort("gpt-5") is False
