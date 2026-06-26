# GoNoGo — Phase 3 for Antigravity — Report Assembly + Remaining Guardrails

> Copy everything below into Antigravity as your message once Phase 2 is done and committed. `SPEC.md` and `data/regions.json` are already in the repo — re-read `SPEC.md` instead of asking me to re-paste it.

## Context for this phase

Phase 1 gave us the deterministic fetch + rule engine. Phase 2 gave us the agent pipeline producing notes + a top recommendation. This phase assembles the actual full report described in `SPEC.md`'s "Overview dashboard" section, and adds the remaining quality/observability items.

## Your job in this phase

1. Build the full report assembly: top recommendation pinned above, then all 12 regions sorted north→south, each showing its Advisor note and **three stacked tier-tables** (base/mid/peak) — each table being the next 3 days × 3 day-parts (morning/midday/evening) = 9 columns of colored cells from Phase 1's rule engine.
2. Add the **Overall column** per region per tier: the worst (most severe) color among that tier-table's visible cells.
3. Add the **48h-rain badge** per region (from Open-Meteo's `past_days`, already fetched in Phase 1/2 — just surface it in the report).
4. Rendering: clean text/markdown output is enough — no real UI/date-picker widget yet, that's a deliberate future step.
5. Add the remaining guardrails and observability from `SPEC.md`:
   - **Scope guardrail**: all computation strictly from `data/regions.json` (defensive check, not just convention).
   - **Lightweight golden-set eval**: 3-5 hardcoded scenarios (mocked weather → obviously-correct outcome) checked with simple assertions, without hitting the live Open-Meteo API or costing a real Gemini call where possible.
   - **Structured logging**: JSON-lines log of each agent step (which agent, which tool, summary, latency) for every run.
6. Update the README: exact setup/run steps, plus an explicit "future work" list (cloud deployment, peak-level drill-down UI, chat interface, persistent memory, real date-picker UI) so it's clear these are deferred, not forgotten.

## Before you write code

Produce a short task list / implementation plan first and pause for my review.

## Definition of done for this phase (and effectively for the whole MVP)

- Running the CLI with a sample date and a sample date range each produce the full report: top recommendation, then all 12 regions north→south, each with a note and 3 tier-tables with correct Overall-column logic and a 48h-rain badge.
- The golden-set eval runs and passes without hitting the live Open-Meteo API or costing more than a small fixed number of Gemini calls.
- A log file shows the full per-agent, per-tool trace after a run.
- `SPEC.md` in the repo still matches what was actually built — update it if anything drifted during implementation.
- Manually verify at least one hand-checked example (pick a region, confirm the Overall color logic is right) rather than just "it runs without errors."
