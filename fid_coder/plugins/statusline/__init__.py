"""Status line plugin — a customizable bottom status line for Fid Coder.

Mirrors Claude Code's ``statusLine`` feature: you configure a shell command;
Fid Coder feeds it JSON session data on stdin; whatever the command prints to
stdout becomes your status line (ANSI colors supported).

Configure with the ``/statusline`` command or directly via ``/set``:

    /set statusline_enabled=true
    /set statusline_command=~/.fid_coder/statusline.sh

The command runs throttled in a background thread, so it never blocks the
prompt. Run ``/statusline json`` to see every field your script receives.
"""
