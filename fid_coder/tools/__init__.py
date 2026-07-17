import os

from fid_coder.callbacks import on_register_agent_tools, on_register_tools
from fid_coder.messaging import emit_warning
from fid_coder.tools.agent_tools import register_list_agents
from fid_coder.tools.ask_user_question import register_ask_user_question

# Browser automation tools
from fid_coder.tools.browser.browser_control import (
    register_close_browser,
    register_create_new_page,
    register_get_browser_status,
    register_initialize_browser,
    register_list_pages,
)
from fid_coder.tools.browser.browser_interactions import (
    register_browser_check,
    register_browser_uncheck,
    register_click_element,
    register_double_click_element,
    register_get_element_text,
    register_get_element_value,
    register_hover_element,
    register_select_option,
    register_set_element_text,
)
from fid_coder.tools.browser.browser_locators import (
    register_find_buttons,
    register_find_by_label,
    register_find_by_placeholder,
    register_find_by_role,
    register_find_by_test_id,
    register_find_by_text,
    register_find_links,
    register_run_xpath_query,
)
from fid_coder.tools.browser.browser_navigation import (
    register_browser_go_back,
    register_browser_go_forward,
    register_get_page_info,
    register_navigate_to_url,
    register_reload_page,
    register_wait_for_load_state,
)
from fid_coder.tools.browser.browser_page_snapshot import (
    register_get_page_snapshot,
)
from fid_coder.tools.browser.browser_screenshot import (
    register_take_screenshot_and_analyze,
)
from fid_coder.tools.browser.browser_scripts import (
    register_browser_clear_highlights,
    register_browser_highlight_element,
    register_execute_javascript,
    register_scroll_page,
    register_scroll_to_element,
    register_set_viewport_size,
    register_wait_for_element,
)
from fid_coder.tools.browser.browser_semantic_interactions import (
    register_click_by_role,
    register_click_by_text,
    register_set_text_by_label,
)
from fid_coder.tools.browser.browser_workflows import (
    register_list_workflows,
    register_read_workflow,
    register_save_workflow,
)
from fid_coder.tools.command_runner import (
    register_agent_run_shell_command,
    register_agent_share_your_reasoning,
)
from fid_coder.tools.display import (
    display_non_streamed_result as display_non_streamed_result,
)
from fid_coder.tools.file_modifications import (
    register_create_file,
    register_delete_file,
    register_delete_snippet,
    register_edit_file,
    register_replace_in_file,
)
from fid_coder.tools.file_operations import (
    register_grep,
    register_list_files,
    register_read_file,
)
from fid_coder.tools.image_tools import register_load_image
from fid_coder.tools.model_tools import register_list_available_models
from fid_coder.tools.skills_tools import (
    register_activate_skill,
    register_list_or_search_skills,
)
from fid_coder.tools.subagent_invocation import (
    register_invoke_agent,
    register_invoke_agent_with_model,
)

# Map of tool names to their individual registration functions
TOOL_REGISTRY = {
    # Agent Tools
    "list_agents": register_list_agents,
    "invoke_agent": register_invoke_agent,
    "invoke_agent_with_model": register_invoke_agent_with_model,
    "list_available_models": register_list_available_models,
    # File Operations
    "list_files": register_list_files,
    "read_file": register_read_file,
    "grep": register_grep,
    # File Modifications
    "edit_file": register_edit_file,  # DEPRECATED: auto-expanded
    "create_file": register_create_file,
    "replace_in_file": register_replace_in_file,
    "delete_snippet": register_delete_snippet,
    "delete_file": register_delete_file,
    # Command Runner
    "agent_run_shell_command": register_agent_run_shell_command,
    "agent_share_your_reasoning": register_agent_share_your_reasoning,
    # User Interaction
    "ask_user_question": register_ask_user_question,
    # Browser Control
    "browser_initialize": register_initialize_browser,
    "browser_close": register_close_browser,
    "browser_status": register_get_browser_status,
    "browser_new_page": register_create_new_page,
    "browser_list_pages": register_list_pages,
    # Browser Navigation
    "browser_navigate": register_navigate_to_url,
    "browser_get_page_info": register_get_page_info,
    "browser_go_back": register_browser_go_back,
    "browser_go_forward": register_browser_go_forward,
    "browser_reload": register_reload_page,
    "browser_wait_for_load": register_wait_for_load_state,
    # Browser Element Discovery
    "browser_find_by_role": register_find_by_role,
    "browser_find_by_text": register_find_by_text,
    "browser_find_by_label": register_find_by_label,
    "browser_find_by_placeholder": register_find_by_placeholder,
    "browser_find_by_test_id": register_find_by_test_id,
    "browser_xpath_query": register_run_xpath_query,
    "browser_find_buttons": register_find_buttons,
    "browser_find_links": register_find_links,
    # Browser Semantic Interactions (accessibility-first, DOM progression)
    "browser_page_snapshot": register_get_page_snapshot,
    "browser_click_by_role": register_click_by_role,
    "browser_click_by_text": register_click_by_text,
    "browser_set_text_by_label": register_set_text_by_label,
    # Browser Element Interactions
    "browser_click": register_click_element,
    "browser_double_click": register_double_click_element,
    "browser_hover": register_hover_element,
    "browser_set_text": register_set_element_text,
    "browser_get_text": register_get_element_text,
    "browser_get_value": register_get_element_value,
    "browser_select_option": register_select_option,
    "browser_check": register_browser_check,
    "browser_uncheck": register_browser_uncheck,
    # Browser Scripts and Advanced Features
    "browser_execute_js": register_execute_javascript,
    "browser_scroll": register_scroll_page,
    "browser_scroll_to_element": register_scroll_to_element,
    "browser_set_viewport": register_set_viewport_size,
    "browser_wait_for_element": register_wait_for_element,
    "browser_highlight_element": register_browser_highlight_element,
    "browser_clear_highlights": register_browser_clear_highlights,
    # Browser Screenshots
    "browser_screenshot_analyze": register_take_screenshot_and_analyze,
    # Browser Workflows
    "browser_save_workflow": register_save_workflow,
    "browser_list_workflows": register_list_workflows,
    "browser_read_workflow": register_read_workflow,
    # Image loading (used by browser/QA agents and friends)
    "load_image_for_analysis": register_load_image,
    # Skills Tools
    "activate_skill": register_activate_skill,
    "list_or_search_skills": register_list_or_search_skills,
}

# Tools that expand into multiple tools for backward compatibility.
TOOL_EXPANSIONS: dict[str, list[str]] = {
    "edit_file": ["create_file", "replace_in_file", "delete_snippet"],
}

REMOVED_LEGACY_TOOLS: set[str] = {
    "universal_constructor",
}

# Process-wide tool kill-switch (issue #182). Set via env var for wrappers.
NO_TOOLS_ENV_VAR = "FID_CODER_NO_TOOLS"


def tools_disabled() -> bool:
    """True when the ``FID_CODER_NO_TOOLS`` kill-switch is active."""
    return os.environ.get(NO_TOOLS_ENV_VAR, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _load_plugin_tools() -> None:
    """Load tools registered by plugins into TOOL_REGISTRY."""
    try:
        for result in on_register_tools():
            if result is None:
                continue
            tools_list = result if isinstance(result, list) else [result]
            for tool_def in tools_list:
                if (
                    isinstance(tool_def, dict)
                    and "name" in tool_def
                    and "register_func" in tool_def
                ):
                    register_func = tool_def["register_func"]
                    if callable(register_func):
                        TOOL_REGISTRY[tool_def["name"]] = register_func
    except Exception:
        pass


# Appended to the system prompt when extended thinking is active and
# the share_your_reasoning tool is removed.
EXTENDED_THINKING_PROMPT_NOTE = (
    "\n\nIMPORTANT: You have extended thinking enabled. "
    "Always think between tool calls or waves of tool calls "
    "(if running parallel tools). Use your thinking blocks to reason "
    "about the results before deciding on next steps."
)


def has_extended_thinking_active(model_name: str | None = None) -> bool:
    """Return True when Claude/Anthropic extended thinking is active."""
    from fid_coder.config import get_effective_model_settings, get_global_model_name
    from fid_coder.model_utils import get_default_extended_thinking

    if model_name is None:
        model_name = get_global_model_name()

    if model_name is None:
        return False

    if not (model_name.startswith("claude-") or model_name.startswith("anthropic-")):
        # Copilot Claude models use copilot-claude-* names
        if not (model_name.startswith("copilot-") and "claude" in model_name.lower()):
            return False

    settings = get_effective_model_settings(model_name)
    default_thinking = get_default_extended_thinking(model_name)
    extended_thinking = settings.get("extended_thinking", default_thinking)

    if extended_thinking is True:
        extended_thinking = "enabled"
    elif extended_thinking is False:
        return False

    return extended_thinking in ("enabled", "adaptive")


def register_tools_for_agent(
    agent,
    tool_names: list[str],
    model_name: str | None = None,
    agent_name: str | None = None,
):
    """Register specific tools for an agent based on tool names."""
    if tools_disabled():
        return

    _load_plugin_tools()

    plugin_extras = on_register_agent_tools(agent_name)
    if plugin_extras:
        seen = set(tool_names)
        merged = list(tool_names)
        for extra in plugin_extras:
            if extra not in seen:
                merged.append(extra)
                seen.add(extra)
        tool_names = merged

    expanded_tools: list[str] = []
    seen: set[str] = set()
    for tool_name in tool_names:
        if tool_name in TOOL_EXPANSIONS:
            for expanded in TOOL_EXPANSIONS[tool_name]:
                if expanded not in seen:
                    expanded_tools.append(expanded)
                    seen.add(expanded)
        elif tool_name not in seen:
            expanded_tools.append(tool_name)
            seen.add(tool_name)
    tool_names = expanded_tools

    for tool_name in tool_names:
        if tool_name.startswith("uc:") or tool_name in REMOVED_LEGACY_TOOLS:
            continue

        if tool_name not in TOOL_REGISTRY:
            emit_warning(f"Warning: Unknown tool '{tool_name}' requested, skipping...")
            continue

        TOOL_REGISTRY[tool_name](agent)


def register_all_tools(agent, model_name: str | None = None):
    """Register all available tools to the provided agent."""
    all_tools = list(TOOL_REGISTRY.keys())
    register_tools_for_agent(agent, all_tools, model_name=model_name)


def get_available_tool_names() -> list[str]:
    """Get list of all available tool names."""
    _load_plugin_tools()
    return list(TOOL_REGISTRY.keys())
