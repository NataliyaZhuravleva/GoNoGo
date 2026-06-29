# Fix agents-cli lint issues

## Goal Description
We need to ensure the project passes `agents-cli lint` without errors. The linting process runs Ruff, Codespell, Ty, and optional MyPy checks. Current output shows 29 errors, primarily blank lines with whitespace, import ordering, unnecessary casts, and trailing whitespace.

## User Review Required
- Approve the plan to run automatic formatting (`ruff format .`) and apply safe auto‑fixes (`ruff check . --fix`).
- Approve manual edits for remaining issues (import ordering, unnecessary `int` cast, trailing spaces).

## Open Questions
> (None) – the plan is straightforward.

## Proposed Changes
---
### Core Lint Fixes
- **Run automatic formatter**: `uv run ruff format .` – fixes whitespace, blank lines, import ordering where possible.
- **Run Ruff auto‑fix**: `uv run ruff check . --fix` – applies fixable lint rules (e.g., blank line removal, unused variable fixes already applied).
- **Manual edits** needed after auto‑fixes:
  - Move all imports in `gonogo/fast_api_app.py` to the top of the file (remove the `load_dotenv` call after imports).
  - Remove the redundant `int` cast in `gonogo/core.py` line building the `elevation` query string.
  - Delete trailing whitespace on the `background-image:` line in `fast_api_app.py`.
  - Ensure any remaining `W293` blank‑line whitespace warnings are cleared.
  - Verify imports ordering matches Ruff's `isort` settings (first‑party modules after third‑party).

### Updated Files
- `gonogo/core.py` – remove `int()` around `round(e)`.
- `gonogo/fast_api_app.py` – reorder imports, delete trailing space, clean blank lines.
- Potentially other files with blank‑line whitespace (e.g., `utils.py`, `cli.py`) – `ruff format` will handle.

## Verification Plan
- Run `uv run agents-cli lint`. Expect **0 errors**.
- Run the test suite (`uv run pytest`) to confirm no functional regressions.
- Manually start the server (`uv run python -m gonogo.fast_api_app`) and verify the UI still works.

---
