# Fid Coder Development Guide

> **Golden rule:** nearly all new functionality should be a **plugin** under
> `fid_coder/plugins/` that hooks into core via `fid_coder/callbacks.py`.
> Don't edit `fid_coder/command_line/`.

## Plugins

Drop `register_callbacks.py` in a named subdirectory:

| Tier | Location |
|------|----------|
| Builtin | `fid_coder/plugins/<name>/` |
| User | `~/.fid_coder/plugins/<name>/` |
| Project | `<CWD>/.fid_coder/plugins/<name>/` (trust-gated via `/plugins`) |

```python
from fid_coder.callbacks import register_callback

def _on_startup():
    print("my_feature loaded!")

register_callback("startup", _on_startup)
```

Load order: builtin → user → project. Hook catalogue: `fid_coder/callbacks.py`.

## Rules

1. **Plugins over core** — if a hook exists for it, use it
2. **One `register_callbacks.py` per plugin** — register at module scope
3. **600-line hard cap** — split into submodules
4. **Fail gracefully** — never crash the app
5. **Return `None` from commands you don't own**
6. **Lint with** `ruff check --fix` and `ruff format .`
