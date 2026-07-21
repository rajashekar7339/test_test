"""Semantic slide content for the onboarding wizard.

 Lean, mean, ADHD-friendly slides. Five slides max, because this is
onboarding rather than a hostage situation.
"""

from typing import List, Tuple

SlideContent = list[tuple[str, str]]

MODEL_OPTIONS: List[Tuple[str, str, str]] = [
    (
        "copilot",
        "GitHub Copilot",
        "Sign in with GitHub — uses your Copilot subscription",
    ),
    ("skip", "Skip for now", "Configure later with /copilot-login"),
]


def _add(content: SlideContent, style: str, text: str) -> None:
    content.append((style, text))


def get_nav_footer() -> SlideContent:
    """Return semantic navigation hints shown on every slide."""
    return [
        ("class:tui.muted", "\n─────────────────────────────────────\n"),
        ("class:tui.help-key", "→/l"),
        ("class:tui.help", " Next  "),
        ("class:tui.help-key", "←/h"),
        ("class:tui.help", " Back  "),
        ("class:tui.help-key", "↑↓/jk"),
        ("class:tui.help", " Options  "),
        ("class:tui.help-key", "Enter"),
        ("class:tui.help", " Select  "),
        ("class:tui.warning", "ESC"),
        ("class:tui.help", " Skip"),
    ]


def get_gradient_banner() -> SlideContent:
    """Generate the FID CODER banner using the semantic header style."""
    try:
        import pyfiglet

        banner = pyfiglet.figlet_format("FID CODER", font="slant").rstrip()
    except ImportError:
        banner = "═══ FID CODER  ═══"
    return [("class:tui.header", banner)]


def slide_welcome() -> SlideContent:
    """Slide 1: welcome and quick intro."""
    content = get_gradient_banner()
    content.extend(
        [
            ("class:tui.header", "\n\nWelcome! \n\n"),
            ("class:tui.title", "Quick setup:\n"),
            ("class:tui.body", "  1. Sign in with GitHub Copilot\n"),
            ("class:tui.body", "  2. Optional: MCP servers\n"),
            ("class:tui.body", "  3. Learn when to use which agent\n"),
            ("class:tui.body", "  4. Start coding!\n\n"),
            ("class:tui.muted", "Takes ~1 minute. Let's go!"),
        ]
    )
    content.extend(get_nav_footer())
    return content


def slide_models(selected_option: int, options: List[Tuple[str, str]]) -> SlideContent:
    """Slide 2: model selection."""
    content: SlideContent = [
        ("class:tui.header", " Connect GitHub Copilot\n\n"),
        ("class:tui.body", "Fid Coder uses GitHub Copilot for all models.\n\n"),
    ]
    for i, (_, label) in enumerate(options):
        style = "class:tui.selected" if i == selected_option else "class:tui.muted"
        marker = "▶ " if i == selected_option else "  "
        _add(content, style, f"{marker}{label}\n")
    _add(content, "", "\n")

    opt = options[selected_option][0] if options else None
    if opt == "copilot":
        _add(content, "class:tui.warning", " GitHub Copilot\n")
        _add(
            content,
            "class:tui.body",
            "  Sign in with GitHub Device Flow\n"
            "  Models from your Copilot plan (GPT, Claude, etc.)\n",
        )
        _add(content, "class:tui.help-key", "  /copilot-login\n")
    else:
        _add(
            content,
            "class:tui.muted",
            "No worries! Run /copilot-login when you're ready\n",
        )

    content.extend(get_nav_footer())
    return content


def slide_mcp() -> SlideContent:
    """Slide 3: optional MCP server power-ups."""
    content: SlideContent = [
        ("class:tui.header", " MCP Servers (Optional)\n\n"),
        ("class:tui.body", "Supercharge with external tools!\n\n"),
        ("class:tui.title", "Commands:\n"),
        ("class:tui.help-key", "  /mcp install"),
        ("class:tui.body", "  Browse catalog\n"),
        ("class:tui.help-key", "  /mcp list"),
        ("class:tui.body", "     See your servers\n\n"),
        ("class:tui.warning", " Popular picks:\n"),
        (
            "class:tui.body",
            "  • GitHub integration\n  • Postgres/databases\n  • Slack, Linear, etc.\n\n",
        ),
        ("class:tui.muted", "Skip this if you just want to code!"),
    ]
    content.extend(get_nav_footer())
    return content


def slide_use_cases() -> SlideContent:
    """Slide 4: when to use each agent."""
    content: SlideContent = [
        ("class:tui.header", " When to Use What\n\n"),
        ("class:tui.warning", " Fid Coder (default)\n"),
        ("class:tui.success", "  USE FOR:"),
        (
            "class:tui.body",
            " Direct coding tasks\n  • Fix this bug\n  • Add a feature to this file\n  • Refactor this function\n  • Write tests for X\n\n",
        ),
        ("class:tui.warning", " Planning Agent\n"),
        ("class:tui.success", "  USE FOR:"),
        (
            "class:tui.body",
            " Complex multi-step projects\n  • Build me a REST API with auth\n  • Create a CLI tool from scratch\n  • Refactor entire codebase\n  • Multi-file architectural changes\n\n",
        ),
        ("class:tui.help-key", "Switch: /agent planning-agent\n"),
        (
            "class:tui.muted",
            "Planning breaks big tasks into steps,\nthen delegates to specialists.",
        ),
    ]
    content.extend(get_nav_footer())
    return content


def slide_done(trigger_oauth: str | None) -> SlideContent:
    """Slide 5: ready to roll."""
    content: SlideContent = [
        ("class:tui.success", " Ready to Roll!\n\n"),
        ("class:tui.header", "Essential commands:\n"),
        ("class:tui.help-key", "  /model"),
        ("class:tui.body", "   Switch models\n"),
        ("class:tui.help-key", "  /agent"),
        ("class:tui.body", "   Switch agents\n"),
        ("class:tui.help-key", "  /help"),
        ("class:tui.body", "    All commands\n\n"),
        ("class:tui.warning", "Pro tips:\n"),
        (
            "class:tui.body",
            "  • Be specific in prompts\n  • Use Planning Agent for big tasks\n  • @ for file path completion\n\n",
        ),
    ]
    if trigger_oauth == "copilot":
        _add(content, "class:tui.header", "→ GitHub Copilot login next!\n\n")
    content.extend(
        [
            ("class:tui.muted", "Re-run anytime: "),
            ("class:tui.help-key", "/tutorial\n\n"),
            ("class:tui.warning", "Press Enter to start coding! "),
        ]
    )
    content.extend(get_nav_footer())
    return content
