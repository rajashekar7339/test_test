"""Shared agent-name helpers for slash-command completion.

Pinning a model to an agent lives in the ``/agent`` menu (``/pin_model`` and
``/unpin`` were removed as standalone commands). ``AgentCompleter`` uses
these helpers for ``/agent``, ``/a``, ``/switch-agent``, ``/sa`` and
``/fork`` completions.
"""

import json


def _get_pinned_model_for_agent(agent_name: str) -> str | None:
    """Get the pinned model for an agent (config or JSON)."""
    # Check config first (for built-in agents)
    try:
        from fid_coder.config import get_agent_pinned_model

        pinned = get_agent_pinned_model(agent_name)
        if pinned:
            return pinned
    except Exception:
        pass

    # Check if it's a JSON agent with a model key
    try:
        from fid_coder.agents.json_agent import discover_json_agents

        json_agents = discover_json_agents()
        if agent_name in json_agents:
            with open(json_agents[agent_name], "r") as f:
                agent_data = json.load(f)
                return agent_data.get("model")
    except Exception:
        pass

    return None


def _get_agent_display_meta(agent_name: str) -> str:
    """Get display meta for an agent showing pinned model."""
    pinned_model = _get_pinned_model_for_agent(agent_name)
    if pinned_model:
        return f"→ {pinned_model}"
    return "default"


def load_agent_names():
    """Load all available agent names (both built-in and JSON agents)."""
    agents = set()

    # Get built-in agents
    try:
        from fid_coder.agents.agent_manager import get_agent_descriptions

        builtin_agents = get_agent_descriptions()
        agents.update(builtin_agents.keys())
    except Exception:
        pass

    # Get JSON agents
    try:
        from fid_coder.agents.json_agent import discover_json_agents

        json_agents = discover_json_agents()
        agents.update(json_agents.keys())
    except Exception:
        pass

    return sorted(list(agents))
