# GoNoGo Phase 2 Task List

- [x] Add `google-adk[gcp]` dependency to `pyproject.toml` and install
- [x] Run `agents-cli scaffold enhance` to register as an ADK prototype project
- [x] Create the `mountaineering-conditions-skill` directory and `SKILL.md`
- [x] Implement `gonogo/agents.py` containing:
  - `ConditionsAgent`: Deterministic, zero LLM calls, parses and validates weather response
  - `AdvisorAgent`: LLM-based, loads the SkillToolset, generates batched regional notes and top recommendation in one LLM call
  - `OrchestratorAgent`: BaseAgent orchestrating date validation, ConditionsAgent, and AdvisorAgent in sequence, then sorting north-to-south
- [x] Update `gonogo/cli.py` to run the agent runner and print notes and recommendation
- [x] Write unit/integration tests in `tests/test_agents.py` to verify the multi-agent pipeline
- [x] Verify the pipeline runs and tests pass
