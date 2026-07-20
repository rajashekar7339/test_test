"""Tests targeting remaining uncovered lines in fid_coder/agents/ (non-base_agent)."""

import json
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Reviewer agents - get_available_tools and get_system_prompt (2 lines each)
# ---------------------------------------------------------------------------


def _test_reviewer_agent(module_path, class_name):
    """Helper to test reviewer agents' tools and prompt methods."""
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    agent = cls()
    tools = agent.get_available_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    prompt = agent.get_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_qa_kitten():
    from fid_coder.agents.agent_qa_kitten import QualityAssuranceKittenAgent

    agent = QualityAssuranceKittenAgent()
    tools = agent.get_available_tools()
    assert isinstance(tools, list)
    prompt = agent.get_system_prompt()
    assert isinstance(prompt, str)

    # DOM-first progression tools are exposed to qa-kitten (PUP-436).
    for tool in (
        "browser_page_snapshot",
        "browser_click_by_role",
        "browser_click_by_text",
        "browser_set_text_by_label",
    ):
        assert tool in tools

    # Screenshot capability is preserved for visual validation.
    assert "browser_screenshot_analyze" in tools

    # Prompt policy distinguishes non-visual progression from visual validation.
    lowered = prompt.lower()
    assert "dom-first" in lowered
    assert "visual validation" in lowered
    assert "browser_page_snapshot" in prompt
    # Screenshots explicitly scoped to visual assertions, not progression.
    assert "visual assertions" in lowered or "visual assertion" in lowered


def test_fid_coder_agent():
    from fid_coder.agents.agent_fid_coder import FidCoderAgent

    agent = FidCoderAgent()
    tools = agent.get_available_tools()
    assert isinstance(tools, list)
    prompt = agent.get_system_prompt()
    assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# Planning & Prompt Reviewer agents
# ---------------------------------------------------------------------------


def test_planning_agent():
    from fid_coder.agents.agent_planning import PlanningAgent

    agent = PlanningAgent()
    tools = agent.get_available_tools()
    assert isinstance(tools, list)
    prompt = agent.get_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_fid_coder_prompt_allows_callback_additions():
    from fid_coder.agents.agent_fid_coder import FidCoderAgent

    agent = FidCoderAgent()
    # ``load_prompt`` fragments now live in get_full_system_prompt (BaseAgent),
    # not in the authored get_system_prompt.
    with patch("fid_coder.callbacks.on_load_prompt", return_value=["extra"]):
        prompt = agent.get_full_system_prompt()
        assert "extra" in prompt


def test_fid_coder_authored_prompt_excludes_runtime_additions():
    """Authored prompt must NOT contain load_prompt fragments or the identity.

    Regression for the clone bug: cloning persists get_system_prompt(), so
    runtime-only metadata (kennel memory, live timestamps) and the per-instance
    identity ID must stay out of it.
    """
    from fid_coder.agents.agent_fid_coder import FidCoderAgent

    agent = FidCoderAgent()
    with patch("fid_coder.callbacks.on_load_prompt", return_value=["SECRET-RUNTIME"]):
        authored = agent.get_system_prompt()
    assert "SECRET-RUNTIME" not in authored
    assert agent.get_identity() not in authored


# ---------------------------------------------------------------------------
# agent_creator_agent.py - lines 45-46, 52, 546-626
# ---------------------------------------------------------------------------


def test_creator_validate_agent_json_valid():
    """Cover validate_agent_json with valid config."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with patch(
        "fid_coder.agents.agent_creator_agent.get_available_tool_names",
        return_value=["list_files", "read_file"],
    ):
        errors = agent.validate_agent_json(
            {
                "name": "test-agent",
                "description": "A test",
                "system_prompt": "You are a test agent.",
                "tools": ["list_files"],
            }
        )
        assert errors == []


def test_creator_validate_agent_json_missing_fields():
    """Cover missing required fields."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()
    errors = agent.validate_agent_json({})
    assert len(errors) == 4


def test_creator_validate_agent_json_bad_name():
    """Cover name validation: spaces, empty."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with patch(
        "fid_coder.agents.agent_creator_agent.get_available_tool_names",
        return_value=["list_files"],
    ):
        # Space in name
        errors = agent.validate_agent_json(
            {
                "name": "bad name",
                "description": "d",
                "system_prompt": "p",
                "tools": ["list_files"],
            }
        )
        assert any("spaces" in e for e in errors)

        # Empty name
        errors = agent.validate_agent_json(
            {
                "name": "",
                "description": "d",
                "system_prompt": "p",
                "tools": ["list_files"],
            }
        )
        assert any("non-empty" in e for e in errors)


def test_creator_validate_agent_json_bad_tools():
    """Cover tools validation: not a list, invalid tools."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with patch(
        "fid_coder.agents.agent_creator_agent.get_available_tool_names",
        return_value=["list_files"],
    ):
        # tools not a list
        errors = agent.validate_agent_json(
            {
                "name": "test",
                "description": "d",
                "system_prompt": "p",
                "tools": "not-a-list",
            }
        )
        assert any("list" in e for e in errors)

        # invalid tool names
        errors = agent.validate_agent_json(
            {
                "name": "test",
                "description": "d",
                "system_prompt": "p",
                "tools": ["nonexistent_tool"],
            }
        )
        assert any("Invalid" in e for e in errors)


def test_creator_validate_agent_json_bad_prompt():
    """Cover system_prompt validation: not string/list, bad list items."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with patch(
        "fid_coder.agents.agent_creator_agent.get_available_tool_names",
        return_value=["list_files"],
    ):
        # prompt is number
        errors = agent.validate_agent_json(
            {
                "name": "test",
                "description": "d",
                "system_prompt": 123,
                "tools": ["list_files"],
            }
        )
        assert any("string or list" in e for e in errors)

        # prompt is list with non-strings
        errors = agent.validate_agent_json(
            {
                "name": "test",
                "description": "d",
                "system_prompt": ["ok", 123],
                "tools": ["list_files"],
            }
        )
        assert any("must be strings" in e for e in errors)


def test_creator_get_agent_file_path():
    """Cover get_agent_file_path."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()
    with patch(
        "fid_coder.agents.agent_creator_agent.get_user_agents_directory",
        return_value="/tmp/agents",
    ):
        path = agent.get_agent_file_path("my-agent")
        assert path.endswith("my-agent.json")


def test_creator_create_agent_json_success(tmp_path):
    """Cover create_agent_json success path."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with (
        patch(
            "fid_coder.agents.agent_creator_agent.get_available_tool_names",
            return_value=["list_files"],
        ),
        patch(
            "fid_coder.agents.agent_creator_agent.get_user_agents_directory",
            return_value=str(tmp_path),
        ),
    ):
        success, msg = agent.create_agent_json(
            {
                "name": "new-agent",
                "description": "d",
                "system_prompt": "p",
                "tools": ["list_files"],
            }
        )
        assert success is True
        assert "Successfully" in msg
        assert (tmp_path / "new-agent.json").exists()


def test_creator_create_agent_json_already_exists(tmp_path):
    """Cover create_agent_json when file exists."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()
    (tmp_path / "existing.json").write_text("{}")

    with (
        patch(
            "fid_coder.agents.agent_creator_agent.get_available_tool_names",
            return_value=["list_files"],
        ),
        patch(
            "fid_coder.agents.agent_creator_agent.get_user_agents_directory",
            return_value=str(tmp_path),
        ),
    ):
        success, msg = agent.create_agent_json(
            {
                "name": "existing",
                "description": "d",
                "system_prompt": "p",
                "tools": ["list_files"],
            }
        )
        assert success is False
        assert "already exists" in msg


def test_creator_create_agent_json_validation_error():
    """Cover create_agent_json with validation errors."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()
    success, msg = agent.create_agent_json({})
    assert success is False
    assert "Validation" in msg


def test_creator_create_agent_json_write_failure(tmp_path):
    """Cover create_agent_json write failure."""
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()

    with (
        patch(
            "fid_coder.agents.agent_creator_agent.get_available_tool_names",
            return_value=["list_files"],
        ),
        patch(
            "fid_coder.agents.agent_creator_agent.get_user_agents_directory",
            return_value=str(tmp_path),
        ),
        patch("builtins.open", side_effect=PermissionError("denied")),
    ):
        success, msg = agent.create_agent_json(
            {
                "name": "fail-agent",
                "description": "d",
                "system_prompt": "p",
                "tools": ["list_files"],
            }
        )
        assert success is False
        assert "Failed" in msg


def test_creator_get_user_prompt():
    from fid_coder.agents.agent_creator_agent import AgentCreatorAgent

    agent = AgentCreatorAgent()
    prompt = agent.get_user_prompt()
    assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# agent_manager.py - lines 86-90, 247, 267-279, 585, 673-674
# ---------------------------------------------------------------------------


def test_agent_manager_is_process_alive_dead_process():
    """Cover ProcessLookupError branch in _is_process_alive."""
    import sys

    from fid_coder.agents.agent_manager import _is_process_alive

    if sys.platform == "win32":
        pytest.skip("Unix-only")
    with patch("os.kill", side_effect=ProcessLookupError):
        result = _is_process_alive(999999999)
        assert result is False


def test_agent_manager_is_process_alive_permission():
    """Cover PermissionError branch (process exists but no permission)."""
    import sys

    from fid_coder.agents.agent_manager import _is_process_alive

    if sys.platform == "win32":
        pytest.skip("Unix-only")
    with patch("os.kill", side_effect=PermissionError):
        result = _is_process_alive(999999999)
        assert result is True


def test_agent_manager_discover_agents_error():
    """Cover error loading agent sub-packages (lines 267-279)."""
    from fid_coder.agents.agent_manager import _discover_agents

    # Should not raise even with import errors
    with patch("importlib.import_module", side_effect=Exception("boom")):
        _discover_agents()  # Should not raise


def test_next_clone_index():
    """Cover _next_clone_index (line 585)."""
    from pathlib import Path

    from fid_coder.agents.agent_manager import _next_clone_index

    # No existing clones
    with patch("pathlib.Path.exists", return_value=False):
        idx = _next_clone_index("test", [], Path("/tmp"))
        assert isinstance(idx, int)
        assert idx >= 1

    # With existing clones
    with patch("pathlib.Path.exists", return_value=False):
        idx = _next_clone_index("test", ["test-clone-1", "test-clone-3"], Path("/tmp"))
        assert idx >= 1


def test_clone_agent_failure():
    """Cover clone_agent failure paths (lines 673-674)."""
    from fid_coder.agents.agent_manager import clone_agent

    with patch("fid_coder.agents.agent_manager.emit_warning"):
        result = clone_agent("totally-nonexistent-agent-xyz")
        # Should return None for nonexistent agent
        assert result is None


def test_clone_class_agent_does_not_bake_runtime_metadata(tmp_path):
    """Cloning a class-based agent must persist only the authored prompt.

    Regression: previously the clone stored ``get_full_system_prompt()`` which
    baked in runtime ``load_prompt`` fragments (kennel memory, live
    timestamps/CWD) and the per-instance identity ID into the static JSON.
    """
    import fid_coder.agents.agent_manager as am
    from fid_coder.agents.agent_fid_coder import FidCoderAgent

    captured = {}

    def fake_atomic_write(path, content):
        captured["path"] = path
        captured["content"] = content

    with (
        patch.object(am, "_discover_agents"),
        patch.dict(am._AGENT_REGISTRY, {"fid-coder": FidCoderAgent}, clear=True),
        patch(
            "fid_coder.config.get_user_agents_directory",
            return_value=str(tmp_path),
        ),
        patch("fid_coder.config.get_agent_pinned_model", return_value=None),
        patch(
            "fid_coder.callbacks.on_load_prompt",
            return_value=["KENNEL-SECRET-BLOCK"],
        ),
        patch.object(am, "atomic_write_text", side_effect=fake_atomic_write),
        patch.object(am, "emit_success"),
        patch.object(am, "emit_warning"),
        patch.object(am, "_filter_available_tools", side_effect=lambda t: t),
    ):
        clone_name = am.clone_agent("fid-coder")

    assert clone_name == "fid-coder-clone-1"
    config = json.loads(captured["content"])
    # Runtime-only metadata must not be frozen into the clone definition.
    assert "KENNEL-SECRET-BLOCK" not in config["system_prompt"]
    # No baked identity ID block.
    assert "Your ID is" not in config["system_prompt"]


# ---------------------------------------------------------------------------
# event_stream_handler.py - lines 45-48, 262-263, 285
# ---------------------------------------------------------------------------


def test_fire_stream_event_import_error():
    """Cover ImportError branch in _fire_stream_event."""
    from fid_coder.agents.event_stream_handler import _fire_stream_event

    with patch("fid_coder.callbacks.on_stream_event", side_effect=ImportError):
        _fire_stream_event("test", {})  # Should not raise


def test_fire_stream_event_exception():
    """Cover Exception branch in _fire_stream_event."""
    from fid_coder.agents.event_stream_handler import _fire_stream_event

    with patch("fid_coder.callbacks.on_stream_event", side_effect=Exception("boom")):
        _fire_stream_event("test", {})  # Should not raise


# ---------------------------------------------------------------------------
# json_agent.py - lines 103-109, 118
# ---------------------------------------------------------------------------


def _make_json_agent(tmp_path, config):
    """Helper to create a JSONAgent from a dict config."""
    from fid_coder.agents.json_agent import JSONAgent

    path = tmp_path / f"{config['name']}.json"
    path.write_text(json.dumps(config))
    return JSONAgent(str(path))


def test_json_agent_get_user_prompt(tmp_path):
    """Cover get_user_prompt."""
    agent = _make_json_agent(
        tmp_path,
        {
            "name": "t",
            "display_name": "T",
            "description": "d",
            "system_prompt": "p",
            "tools": [],
            "user_prompt": "hello there",
        },
    )
    assert agent.get_user_prompt() == "hello there"


# ---------------------------------------------------------------------------
# subagent_stream_handler.py - lines 59, 152-155
# ---------------------------------------------------------------------------


def test_subagent_fire_callback_no_loop():
    """Cover RuntimeError branch (no event loop) in _fire_callback."""
    from fid_coder.agents.subagent_stream_handler import _fire_callback

    # Called outside async context - should not raise
    _fire_callback("test", {}, None)


def test_subagent_fire_callback_import_error():
    """Cover ImportError branch in _fire_callback."""
    from fid_coder.agents.subagent_stream_handler import _fire_callback

    with patch("fid_coder.callbacks.on_stream_event", side_effect=ImportError):
        _fire_callback("test", {}, None)


def test_subagent_stream_handler_module():
    """Verify the module is importable."""
    import importlib

    mod = importlib.import_module("fid_coder.agents.subagent_stream_handler")
    assert hasattr(mod, "_fire_callback")
