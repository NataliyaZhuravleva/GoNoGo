# Implementation Plan - GoNoGo (Phase 3.5: Remove Date Inputs & Default to 7-Day Week)

This plan covers removing user date inputs from both the CLI and web dashboard, defaulting to a static 7-day forecast starting tomorrow (clamped to Open-Meteo's reliable horizon), and updating the corresponding documentation.

## User Review Required

> [!IMPORTANT]
> - **CLI Arguments**: The `--date` and `--end-date` arguments will be removed from the CLI. Running `uv run python -m gonogo.cli` will always return the weekly conditions board.
> - **Web Dashboard**: The date input fields will be removed from the controls card. A single "Refresh Conditions" button will be provided to trigger updates.
> - **Backward Compatibility**: To keep existing tests (which pass specific dates to mock inputs) functional, the backend `OrchestratorAgent` will attempt to parse dates if they are provided, but default to the 7-day weekly forecast if they are missing or invalid.

## Proposed Changes

### 1. Agents Logic (`gonogo/agents.py`)
- Modify `OrchestratorAgent._run_async_impl` to check if a date range (YYYY-MM-DD) is specified in the user query.
- If no date range is provided, default to:
  - `start_date = date.today() + timedelta(days=1)` (tomorrow)
  - `end_date = start_date + timedelta(days=6)` (7-day forecast range)
- This ensures compatibility with unit/E2E test queries (which pass dates) while defaulting to the full week for the UI and CLI.

### 2. FastAPI Backend & Dashboard (`gonogo/fast_api_app.py`)
- Update the `/api/report` endpoint to make `start_date` and `end_date` query parameters optional (`str | None = None`). If they are not supplied, default to the weekly range (tomorrow -> tomorrow + 6 days).
- In `/dashboard` (the HTML template):
  - Remove `<input type="date" id="start-date">` and `<input type="date" id="end-date">` from the DOM controls card.
  - Set up a single button styled as `Refresh Conditions`.
  - Update `loadReport()` JavaScript to call `/api/report` without date parameters, fetching the weekly data automatically.

### 3. CLI Application (`gonogo/cli.py`)
- Modify the arguments parser in `main()` to remove the `--date` and `--end-date` options.
- Update `run_pipeline()` to call the orchestrator with an empty query (which triggers the 7-day default range).
- The console tables output will dynamically adjust to print all 7 days of the forecast automatically.

### 4. Documentation (`README.md` and `SPEC.md`)
- Update `README.md` to remove instructions for specifying `--date` and `--end-date`.
- Update `SPEC.md` to clarify that the application operates on a default 7-day weekly horizon and no longer accepts date range inputs.

---

## Verification Plan

### Automated Tests
Run the test suite:
```bash
uv run pytest
```
Verify that all 22 tests pass cleanly (including the `test_chat_stream` integration test which was previously failing due to date parsing requirements).

### Manual Verification
1. **CLI Run**:
   Run the CLI:
   ```bash
   uv run python -m gonogo.cli
   ```
   Verify that it displays a 7-day conditions table (from tomorrow to tomorrow + 6 days) without requiring date inputs.
2. **Web Dashboard**:
   Run the server:
   ```bash
   uv run python -m gonogo.fast_api_app
   ```
   Verify that the date inputs are removed and clicking `Refresh Conditions` successfully fetches and displays the weekly conditions.
