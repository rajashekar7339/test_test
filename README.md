# Fid Coder

AI coding agent (GitHub Copilot). Distributed via git — clone this repo, then run.

## Prerequisites

- Git
- Python 3.11–3.14
- [uv](https://docs.astral.sh/uv/)

## bash (macOS / Linux)

```bash
git clone <repo-url> fid_coder
cd fid_coder

curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --no-editable
./fid -i
```

## Windows (PowerShell)

```powershell
git clone <repo-url> fid_coder
cd fid_coder

powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync --no-editable
uv run --no-editable fid-coder -i
```

## First run (inside the app)

```text
/copilot-login
/add_model    # browse Copilot models (Claude, GPT, …) and add one
/model        # switch among registered models
```

## Browser agent (optional)

```bash
uv run playwright install chromium
```

Then use the `qa-kitten` agent. For a visible window: `BROWSER_HEADLESS=false`.
