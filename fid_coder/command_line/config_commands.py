"""Command handlers for Fid Coder - CONFIG commands.

This module contains @register_command decorated handlers that are automatically
discovered by the command registry system.
"""

from typing import Optional

from fid_coder.command_line.command_registry import register_command
from fid_coder.command_line.config_apply import apply_setting


# Import get_commands_help from command_handler to avoid circular imports
# This will be defined in command_handler.py
def get_commands_help():
    """Lazy import to avoid circular dependency."""
    from fid_coder.command_line.command_handler import get_commands_help as _gch

    return _gch()


@register_command(
    name="show",
    description="Show fid config key-values",
    usage="/show",
    category="config",
)
def handle_show_command(command: str) -> bool:
    """Show current fid configuration."""
    from rich.text import Text

    from fid_coder.agents import get_current_agent
    from fid_coder.command_line.model_picker_completion import get_active_model
    from fid_coder.config import (
        get_auto_save_session,
        get_compaction_strategy,
        get_compaction_threshold,
        get_default_agent,
        get_effective_temperature,
        get_openai_reasoning_effort,
        get_openai_verbosity,
        get_owner_name,
        get_protected_token_count,
        get_fid_name,
        get_resume_message_count,
        get_temperature,
        get_yolo_mode,
    )
    from fid_coder.keymap import (
        get_cancel_agent_display_name,
    )
    from fid_coder.messaging import emit_info

    fid_name = get_fid_name()
    owner_name = get_owner_name()
    model = get_active_model()
    yolo_mode = get_yolo_mode()
    auto_save = get_auto_save_session()
    protected_tokens = get_protected_token_count()
    compaction_threshold = get_compaction_threshold()
    compaction_strategy = get_compaction_strategy()
    global_temperature = get_temperature()
    effective_temperature = get_effective_temperature(model)

    # Get current agent info
    current_agent = get_current_agent()
    default_agent = get_default_agent()

    status_msg = f"""[bold magenta]◆ Fid Status[/bold magenta]

[bold]fid_name:[/bold]            [cyan]{fid_name}[/cyan]
[bold]owner_name:[/bold]            [cyan]{owner_name}[/cyan]
[bold]current_agent:[/bold]         [magenta]{current_agent.display_name}[/magenta]
[bold]default_agent:[/bold]        [cyan]{default_agent}[/cyan]
[bold]model:[/bold]                 [green]{model}[/green]
[bold]YOLO_MODE:[/bold]             {"[red]ON[/red]" if yolo_mode else "[yellow]off[/yellow]"}
[bold]auto_save_session:[/bold]     {"[green]enabled[/green]" if auto_save else "[yellow]disabled[/yellow]"}
[bold]protected_tokens:[/bold]      [cyan]{protected_tokens:,}[/cyan] recent tokens preserved
[bold]compaction_threshold:[/bold]     [cyan]{compaction_threshold:.1%}[/cyan] context usage triggers compaction
[bold]compaction_strategy:[/bold]   [cyan]{compaction_strategy}[/cyan] (summarization or truncation)
[bold]resume_message_count:[/bold] [cyan]{get_resume_message_count()}[/cyan] messages shown on /resume
[bold]reasoning_effort:[/bold]      [cyan]{get_openai_reasoning_effort()}[/cyan]
[bold]verbosity:[/bold]             [cyan]{get_openai_verbosity()}[/cyan]
[bold]temperature:[/bold]           [cyan]{effective_temperature if effective_temperature is not None else "(model default)"}[/cyan]{" (per-model)" if effective_temperature != global_temperature and effective_temperature is not None else ""}
[bold]cancel_agent_key:[/bold]      [cyan]{get_cancel_agent_display_name()}[/cyan] (options: ctrl+c, ctrl+k, ctrl+q)

"""
    emit_info(Text.from_markup(status_msg))
    return True


@register_command(
    name="set",
    description="Set fid config (e.g., /set yolo_mode true) or launch interactive menu",
    usage="/set [key [value]]",
    category="config",
)
def handle_set_command(command: str) -> bool:
    """Set configuration values, or launch the interactive picker."""
    from fid_coder.messaging import emit_error, emit_info, emit_success, emit_warning

    tokens = command.split(None, 2)
    argstr = command[len("/set") :].strip()
    key: Optional[str] = None
    value: Optional[str] = None
    if "=" in argstr:
        key, value = argstr.split("=", 1)
        key = key.strip()
        value = value.strip()
    elif len(tokens) >= 3:
        key = tokens[1]
        value = tokens[2]
    elif len(tokens) == 2:
        key = tokens[1]
        value = ""
    else:
        # No arguments -- launch the interactive config menu
        _launch_interactive_set_menu()
        return True

    if not key:
        emit_error("You must supply a key.")
        return True

    result = apply_setting(key, value or "", reload_agent=True)
    if not result.ok:
        emit_error(result.error or "Failed to apply setting.")
        return True

    from fid_coder.command_line.set_menu_values import is_sensitive_key, mask_value

    display = (
        mask_value(result.value_after or "")
        if is_sensitive_key(key)
        else result.value_after
    )
    if key == "yolo_mode" and (value or "").strip().lower() == "config":
        emit_success("Using YOLO mode from fid.cfg; configuration unchanged.")
    else:
        emit_success(f'Set {key} = "{display}" in fid.cfg!')
    # Restart notices (warning) and the reload-success/failure signal
    # are independent: a restart-required key like ``enable_dbos``
    # should still report whether the live agent reload happened. The
    # original ``/set`` always emitted "Agent reloaded with updated
    # config" alongside the restart notice; preserve that contract.
    if result.warning:
        emit_warning(result.warning)
    if result.reload_error:
        emit_warning(result.reload_error)
    else:
        emit_info("Agent reloaded with updated config")
    return True


def _launch_interactive_set_menu() -> None:
    """Run the picker in a worker thread and drain any queued messages.

    The picker owns the terminal while prompt_toolkit is active, so it
    can't safely emit messages itself; instead it returns them in
    ``PickerResult.pending_messages`` and we emit them here on the
    main thread once the picker has fully exited.
    """
    import asyncio
    import concurrent.futures

    from fid_coder.command_line.set_menu import interactive_set_picker
    from fid_coder.messaging import emit_error, emit_info, emit_success, emit_warning

    _LEVEL_EMITTERS = {
        "info": emit_info,
        "success": emit_success,
        "warning": emit_warning,
        "error": emit_error,
    }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: asyncio.run(interactive_set_picker()))
        result = future.result(timeout=300)  # 5 min timeout

    if result is None:
        return
    for level, message in result.pending_messages:
        emitter = _LEVEL_EMITTERS.get(level, emit_info)
        emitter(message)

    # Coalesce all agent reloads into a single one at the end, but only
    # when the user actually changed something. Failures here mirror the
    # behaviour of the per-key path: warn, don't crash.
    if result.changed_settings:
        from fid_coder.agents import get_current_agent

        try:
            get_current_agent().reload_code_generation_agent()
            emit_info("Agent reloaded with updated config")
        except Exception as reload_error:
            emit_warning(f"Config saved but agent reload failed: {reload_error}")


# /pin_model and /unpin removed — pin/unpin via the /agent menu.


@register_command(
    name="diff",
    description="Configure diff highlighting colors (additions, deletions)",
    usage="/diff",
    category="config",
)
def handle_diff_command(command: str) -> bool:
    """Configure diff highlighting colors."""
    import asyncio
    import concurrent.futures

    from fid_coder.command_line.diff_menu import interactive_diff_picker
    from fid_coder.config import (
        set_diff_addition_color,
        set_diff_deletion_color,
    )
    from fid_coder.messaging import emit_error

    # Show interactive picker for diff configuration
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: asyncio.run(interactive_diff_picker()))
        result = future.result(timeout=300)  # 5 min timeout

    if result:
        # Apply the changes silently (no console output)
        try:
            set_diff_addition_color(result["add_color"])
            set_diff_deletion_color(result["del_color"])
        except Exception as e:
            emit_error(f"Failed to apply diff settings: {e}")
    return True


# /colors removed — banner colors stay on DEFAULT_BANNER_COLORS (and /theme if used).


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _show_color_options(color_type: str):
    # ============================================================================
    # UTILITY FUNCTIONS
    # ============================================================================

    """Show available Rich color options organized by category."""
    from rich.text import Text

    from fid_coder.messaging import emit_info

    # Standard Rich colors organized by category
    color_categories = {
        "Basic Colors": [
            ("black", "⚫"),
            ("red", "🔴"),
            ("green", "🟢"),
            ("yellow", "🟡"),
            ("blue", "🔵"),
            ("magenta", "🟣"),
            ("cyan", "🔷"),
            ("white", "⚪"),
        ],
        "Bright Colors": [
            ("bright_black", "⚫"),
            ("bright_red", "🔴"),
            ("bright_green", "🟢"),
            ("bright_yellow", "🟡"),
            ("bright_blue", "🔵"),
            ("bright_magenta", "🟣"),
            ("bright_cyan", "🔷"),
            ("bright_white", "⚪"),
        ],
        "Special Colors": [
            ("orange1", "🟠"),
            ("orange3", "🟠"),
            ("orange4", "🟠"),
            ("deep_sky_blue1", "🔷"),
            ("deep_sky_blue2", "🔷"),
            ("deep_sky_blue3", "🔷"),
            ("deep_sky_blue4", "🔷"),
            ("turquoise2", "🔷"),
            ("turquoise4", "🔷"),
            ("steel_blue1", "🔷"),
            ("steel_blue3", "🔷"),
            ("chartreuse1", "🟢"),
            ("chartreuse2", "🟢"),
            ("chartreuse3", "🟢"),
            ("chartreuse4", "🟢"),
            ("gold1", "🟡"),
            ("gold3", "🟡"),
            ("rosy_brown", "🔴"),
            ("indian_red", "🔴"),
        ],
    }

    # Suggested colors for each type
    if color_type == "additions":
        suggestions = [
            ("green", "🟢"),
            ("bright_green", "🟢"),
            ("chartreuse1", "🟢"),
            ("green3", "🟢"),
            ("sea_green1", "🟢"),
        ]
        emit_info(
            Text.from_markup(
                "[bold white on green]🎨 Recommended Colors for Additions:[/bold white on green]"
            )
        )
        for color, emoji in suggestions:
            emit_info(
                Text.from_markup(
                    f"  [cyan]{color:<16}[/cyan] [white on {color}]■■■■■■■■■■[/white on {color}] {emoji}"
                )
            )
    elif color_type == "deletions":
        suggestions = [
            ("orange1", "🟠"),
            ("red", "🔴"),
            ("bright_red", "🔴"),
            ("indian_red", "🔴"),
            ("dark_red", "🔴"),
        ]
        emit_info(
            Text.from_markup(
                "[bold white on orange1]🎨 Recommended Colors for Deletions:[/bold white on orange1]"
            )
        )
        for color, emoji in suggestions:
            emit_info(
                Text.from_markup(
                    f"  [cyan]{color:<16}[/cyan] [white on {color}]■■■■■■■■■■[/white on {color}] {emoji}"
                )
            )

    emit_info("\n🎨 All Available Rich Colors:")
    for category, colors in color_categories.items():
        emit_info(f"\n{category}:")
        # Display in columns for better readability
        for i in range(0, len(colors), 4):
            row = colors[i : i + 4]
            row_text = "  ".join([f"[{color}]■[/{color}] {color}" for color, _ in row])
            emit_info(Text.from_markup(f"  {row_text}"))

    emit_info("\nUsage: /diff {color_type} <color_name>")
    emit_info("All diffs use white text on your chosen background colors")
    emit_info("You can also use hex colors like #ff0000 or rgb(255,0,0)")
