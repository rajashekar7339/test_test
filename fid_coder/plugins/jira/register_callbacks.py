"""Register the Jira plugin's tool, agent, and ``/jira`` command.

No MCP involved: ``read_jira_issue`` is a native tool calling Jira's REST
API directly (see ``client.py``), and the ``jira`` agent is the only
consumer of it in this first slice.
"""

from fid_coder.callbacks import register_callback


def _register_jira_tools() -> list[dict]:
    from .tools import register_read_jira_issue

    return [
        {"name": "read_jira_issue", "register_func": register_read_jira_issue},
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


register_callback("register_tools", _register_jira_tools)
register_callback("register_agents", _register_jira_agents)
register_callback("custom_command_help", _jira_command_help)
register_callback("custom_command", _handle_jira_command)
