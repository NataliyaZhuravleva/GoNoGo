# Implementation Plan - GoNoGo (Phase 2: Agents and Skill)

This plan covers Phase 2 (Google ADK multi-agent integration and skill packaging) of the **GoNoGo** mountaineering conditions board.

## User Review Required

> [!IMPORTANT]
> Please review the proposed multi-agent workflow, skill definition, and answer the open question below.

## Open Questions

1. **Gemini Model Choice**: Which model would you like the Advisor agent to use? We recommend using the standard stable alias `gemini-1.5-flash` or `gemini-2.5-flash` for fast, cost-conscious reasoning. We will default to `gemini-2.5-flash`.

---

## Proposed Project Structure

We will extend the project structure to include the ADK agents and skill package:

```
GoNoGo/
├── .env.example
├── .gitignore
├── LICENSE
├── Makefile
├── pyproject.toml (updated dependencies)
├── README.md
├── SPEC.md
├── data/
│   └── regions.json
├── src/
│   └── gonogo/
│       ├── __init__.py
│       ├── cli.py             # CLI updated to run Orchestrator → Conditions → Advisor
│       ├── core.py            # Headline-peak, date guardrails, weather fetcher
│       ├── rules.py           # Pure deterministic color rule engine
│       ├── utils.py           # Unit conversion, date parsing helpers
│       ├── agents.py          # [NEW] OrchestratorAgent, ConditionsAgent, and AdvisorAgent definitions
│       └── skills/            # [NEW] ADK Skill directory
│           └── mountaineering-conditions-skill/
│               └── SKILL.md   # [NEW] Domain knowledge for mountaineering weather interpretation
└── tests/
    ├── __init__.py
    ├── test_core.py
    ├── test_rules.py
    └── test_agents.py         # [NEW] Unit/integration tests for the ADK agents pipeline
```

---

## Proposed Changes

### 1. Scaffolding Google ADK
- Update `pyproject.toml` to include `google-adk[gcp]>=2.0.0,<3.0.0` under project dependencies.
- Run the enhance command:
  ```bash
  agents-cli scaffold enhance . --agent-directory src/gonogo --prototype --google-api-key --auto-approve
  ```
  This creates the `.google-agents-cli` directory and `agents-cli-manifest.yaml`.
- Run `make install` (`uv pip install -e .[dev]`) to install the newly added ADK library.

### 2. Define Mountaineering Conditions Skill
Create `src/gonogo/skills/mountaineering-conditions-skill/SKILL.md` containing:
- YAML frontmatter with `name: mountaineering-conditions-skill` and a short description.
- Detailed domain instructions outlining wind exposure speed thresholds, freezing level vs. elevation hazards (freeze-thaw and rockfall), precipitation types (rain vs. snow hazards), and navigation/whiteout risks.

### 3. Implement ADK Multi-Agent System (`src/gonogo/agents.py`)
We will implement three custom ADK agents using the ADK SDK:

1. **ConditionsAgent** (deterministic `BaseAgent` subclass):
   - Zero LLM calls.
   - Reads the validated date range from the session state.
   - Invokes Phase 1's `fetch_conditions(start_date, end_date)`.
   - Performs a tool-injection guardrail check: validates that the response maps exactly to the expected JSON schema and Pydantic models (guaranteeing it contains only structured numerical/ISO data and no injection payloads).
   - Writes the structured list of `RegionForecast` objects to `session.state["forecast_data"]`.

2. **AdvisorAgent** (`Agent` / `LlmAgent` instance):
   - LLM-backed (Gemini).
   - Instantiated with the `SkillToolset` loaded from our local skill directory.
   - System instruction directs the agent to evaluate the regions' weather conditions and color verdicts using the `mountaineering-conditions-skill`.
   - Evaluates all 12 regions in **one single batched LLM call**.
   - Outputs: a short condition note per region and a top-pick recommendation (storing them in `session.state`).

3. **OrchestratorAgent** (custom `BaseAgent` wrapper):
   - Acts as the root controller.
   - Validates user input (start/end dates) using the guardrail.
   - Invokes `ConditionsAgent` and then `AdvisorAgent` in sequence.
   - Sorts the regional results north-to-south by latitude.
   - Yields final events containing the structured forecast, region notes, and top recommendation.

### 4. Update the CLI (`src/gonogo/cli.py`)
- Modify `cli.py` to instantiate `OrchestratorAgent` and run it via the ADK `Runner` and `InMemorySessionService`.
- Read the final response, print the top recommendation at the top, and print the 12 regions' agent-written notes sorted north-to-south.

### 5. Write Tests for Agents (`tests/test_agents.py`)
- Test the sequential execution of the agents.
- Verify that `ConditionsAgent` correctly fetches weather data and stores it in session state.
- Verify that `AdvisorAgent` is initialized with the `SkillToolset`.

---

## Verification Plan

### Automated Tests
Run:
```bash
make test
```
This will run the new agent tests along with the core/rule engine tests.

### Manual Verification
Run the updated CLI:
```bash
uv run python -m gonogo.cli --date 2026-06-26
```
We will verify that:
1. Orchestrator, Conditions, and Advisor agents are executed in sequence (confirmed via console outputs or logging).
2. The Advisor's output (notes + top recommendation) is printed.
3. The notes reflect the `mountaineering-conditions-skill` domain knowledge (e.g., highlighting freezing level elevation or wind exposure).
4. Exactly one Gemini call is made by the Advisor, and zero Gemini calls are made by the Conditions agent.
