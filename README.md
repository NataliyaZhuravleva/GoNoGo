# GoNoGo

GoNoGo is a mountaineering conditions board for the Pacific Northwest (PNW). It evaluates current and forecast weather conditions across 12 key regions, helping mountaineers make informed go/no-go decisions based on deterministic, expert-derived rules.

## Setup

The project uses `uv` for python virtual environment and package management.

### Prerequisites

- Python 3.11+
- `uv` installed (`pip install uv` or via brew)

### Installation

1. Install project dependencies and setup edit mode:
   ```bash
   make install
   ```

2. Copy the `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

## Running the CLI

Run the multi-agent conditions checker CLI for tomorrow's forecast (default) or specify a custom date/range:
```bash
# Run for tomorrow's date
uv run python -m gonogo.cli

# Run for a specific date (within next 7 days)
uv run python -m gonogo.cli --date 2026-06-28

# Run for a date range (up to 7 days)
uv run python -m gonogo.cli --date 2026-06-28 --end-date 2026-06-30

# Run without ANSI colors
uv run python -m gonogo.cli --date 2026-06-28 --no-color
```

## Running Tests

Run the complete test suite including unit, integration, and offline golden-set tests:
```bash
make test
```

## Structured Trace Logging

Every execution of the CLI pipeline or agent runner is tracked by the `StructuredLoggingPlugin` and logged to `gonogo_runs.jsonl` in the root directory. Logs are formatted as JSON lines containing:
- `timestamp`: Epoch time of execution.
- `type`: Either `agent` or `tool`.
- `name`: The name of the agent or tool executed.
- `latency_sec`: The execution duration.
- `status`: `success` or error status.
- `summary`: Human-readable summary of the step.
- `args`: Arguments passed to tools (for privacy, content payloads are summarized/truncated).

## Future Work

- **Web Application Dashboard**: Replace the CLI dashboard with a clean, modern browser-based interface utilizing React or Next.js.
- **Trip Report Fetching**: Integrate tools to query real-time trip reports and trail conditions from WTA, AllTrails, and Mountain Project.
- **Expanded Activity Support**: Support ice/rock climbing, backcountry skiing, and gravel biking, with tailored rules engines.
- **Cross-session Memory**: Maintain a history of user queries and favorited regions across sessions.
- **Cloud Deployment**: Package the application container for Cloud Run deployment and setup production telemetry.

## Copyright & Licensing

© 2026 Nataliya Zhuravleva. All rights reserved.

This code is shared publicly for the Kaggle/Google AI Agents Intensive capstone evaluation only. No license is granted for reuse, modification, or redistribution without the author's permission.
