"""Register the Jira plugin's tool, agent, and ``/jira`` command.

No MCP involved: ``read_jira_issue`` is a native tool calling Jira's REST
API directly (see ``client.py``), and the ``jira`` agent is the only
consumer of it in this first slice.
"""

from fid_coder.callbacks import register_callback


def _register_jira_tools() -> list[dict]:
    from .tools import (
        register_jira_login,
        register_read_jira_issue,
        register_search_jira_issues,
    )

    return [
        {"name": "read_jira_issue", "register_func": register_read_jira_issue},
        {"name": "search_jira_issues", "register_func": register_search_jira_issues},
        {"name": "jira_login", "register_func": register_jira_login},
    ]


def _register_jira_agents() -> list[dict]:
    from .agent import JiraAgent

    return [
        {"name": "jira", "class": JiraAgent},
    ]


def _jira_command_help() -> list[tuple[str, str]]:
    from .commands import custom_command_help

    return custom_command_help()


def _handle_jira_command(command: str, name: str):
    from .commands import handle_custom_command

    return handle_custom_command(command, name)


def _on_agent_reload(_agent_id, agent_name: str = "", *args, **kwargs) -> None:
    """When switching to the Jira agent, surface the configured base URL."""
    if str(agent_name).lower() != "jira":
        return
    try:
        from fid_coder.messaging import emit_info, emit_warning

        from .config import get_jira_url

        url = get_jira_url()
        if url:
            emit_info(f"Jira URL: {url}")
        else:
            emit_warning(
                "Jira URL is not set. Tell me your Jira base URL and I'll log "
                "in (e.g. https://jira.<company>.com), or run "
                "`/jira login https://jira.<company>.com`."
            )
    except Exception:
        # Plugins must fail gracefully — never crash agent switch.
        pass


register_callback("register_tools", _register_jira_tools)
register_callback("register_agents", _register_jira_agents)
register_callback("custom_command_help", _jira_command_help)
register_callback("custom_command", _handle_jira_command)
register_callback("agent_reload", _on_agent_reload)
