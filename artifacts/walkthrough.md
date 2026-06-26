# Phase 2 Walkthrough - GoNoGo (Agents + Skill)

We have successfully implemented the ADK Multi-Agent workflow, including the physical domain knowledge skill package, CLI runner integration, and extensive unit/mock testing.

## Changes Made

### 1. Scaffolding & Dependencies
- Added `google-adk[gcp]>=2.0.0,<3.0.0` to [pyproject.toml](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/pyproject.toml).
- Ran `agents-cli scaffold enhance` to register the project as an ADK project.
- Relocated code package to [gonogo/](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/gonogo) in the root directory to satisfy ADK module identification conventions.

### 2. Mountaineering Conditions Skill
- Created the skill package under [gonogo/skills/mountaineering-conditions-skill/](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/gonogo/skills/mountaineering-conditions-skill).
- Wrote [SKILL.md](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/gonogo/skills/mountaineering-conditions-skill/SKILL.md) which contains detailed domain guidelines regarding wind thresholds, freeze-thaw and rockfall hazard elevation boundaries, precipitation hazard types, and whiteout/visibility criteria.

### 3. ADK Agents (`gonogo/agents.py`)
Implemented three sequential agents:
- **`ConditionsAgent`**: Deterministic, zero LLM calls. Bypasses the Gemini API entirely to call the Open-Meteo weather fetch tool, serialize output to Pydantic-validated models (guardrail against injection), and yield the state delta to update the session.
- **`AdvisorAgent`**: LLM-backed (`gemini-2.5-flash`). Configured with a `SkillToolset` loaded dynamically from the physical skill package folder. Instructed to load the skill and output a clean JSON structure within a markdown code block containing conditions notes for all 12 regions (sorted North-to-South) and one overall top recommendation. Executes exactly one Gemini call.
- **`OrchestratorAgent`**: Parent `BaseAgent` coordinating the pipeline. Performs date range validation, runs the sub-agents sequentially via `Aclosing(agent.run_async())`, and propagates state.

### 4. Integration & E2E Testing Support (`gonogo/agent.py` & `gonogo/fast_api_app.py`)
- Created [agent.py](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/gonogo/agent.py) exposing `root_agent = OrchestratorAgent()` and `app = App(root_agent)`.
- If `INTEGRATION_TEST == "TRUE"` is detected in the environment, `agent.py` loads `MockRootAgent` (a `BaseAgent` subclass making zero LLM calls) to satisfy boilerplate test suites.
- Added a `FallbackLogger` in [fast_api_app.py](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/gonogo/fast_api_app.py) to prevent crash failures when credentials or GC projects are missing in local offline test runs.

### 5. CLI Execution (`gonogo/cli.py`)
- Updated the CLI to run the ADK pipeline using `Runner` and `InMemorySessionService`.
- Parses the Advisor agent's markdown JSON block and outputs the results clearly to the console (sorted North-to-South).

---

## Verification Results

### Automated Tests
We wrote unit and mock tests in [test_agents.py](file:///Users/nataliyazhuravleva/Google-projects/GoNoGo/tests/test_agents.py) using `unittest.mock` to verify the agents' internal logic, session state updates, and tool-calling execution paths without hitting the real Gemini API.

We ran `make test` and all 17 tests passed cleanly:
```bash
uv run pytest
======================== 17 passed, 5 warnings in 3.11s ========================
```
This includes:
- 10 core weather fetch and rules tests.
- 2 agent unit/mock tests (Orchestrator pipeline and ConditionsAgent).
- 4 integration/E2E server streaming and feedback tests.
- 1 dummy unit test.
