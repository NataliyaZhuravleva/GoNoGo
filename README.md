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

Run the deterministic conditions checker CLI for tomorrow's forecast (default) or specify a date:
```bash
# Run for default date
uv run python -m gonogo.cli

# Run for a specific date (within next 7 days)
uv run python -m gonogo.cli --date 2026-06-28
```

## Running Tests

Run the unit tests:
```bash
make test
```

## Copyright & Licensing

© 2026 Nataliya Zhuravleva. All rights reserved.

This code is shared publicly for the Kaggle/Google AI Agents Intensive capstone evaluation only. No license is granted for reuse, modification, or redistribution without the author's permission.
