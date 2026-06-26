# GoNoGo — Phase 1 for Antigravity — Setup & Deterministic Core

> Copy everything below into Antigravity as your first message for this project.

I'm starting a new project called **GoNoGo** (name the repo/package `gonogo`). Two files are attached/pasted below in full: `SPEC.md` (project spec) and `regions.json` (the data). Read both fully before doing anything.

---
[PASTE THE FULL CONTENTS OF SPEC.md HERE]
---
[PASTE THE FULL CONTENTS OF regions.json HERE]
---

## Your job in this phase — setup + deterministic core only. No agents, no Gemini calls yet.

1. Scaffold the project (repo layout, dependency management, `.env.example` with `GOOGLE_API_KEY`, `.gitignore`, README stub — project name **GoNoGo**). Add a `LICENSE` file and a copyright line in the README per the "Copyright & licensing" section of `SPEC.md` — ask me for my name/handle to put in the copyright line if it's not obvious from context.
2. Save the spec content above as `SPEC.md` in the repo root, and the data content above as `data/regions.json`, both verbatim.
3. Implement the Open-Meteo batched fetch tool: given the 12 regions' `headline_peak_id` + `tiers` elevations from `data/regions.json`, build the 36 coordinate-elevation pairs and fetch them in **one** multi-location Open-Meteo request. Return clean per-region-per-tier structured forecasts (temperature, precipitation, wind, cloud cover, visibility for the next ~3 days) plus 48h-past precipitation (`past_days` param).
4. Implement the deterministic color-rule engine (thresholds → green/yellow/red) as a pure, unit-testable function — base the thresholds on mountaineering judgment (wind on exposed terrain, freezing level vs. elevation, precip type, visibility); these will later live in the Skill, but for this phase just get the rule engine working and tested as plain code.
5. Implement the date-range guardrail (cap ~7 days, reject malformed/past-only ranges with a clear message).
6. A simple CLI/script to run the fetch + rule engine end-to-end for a sample date and print the raw 12×3 tier data with colors — no agents, no notes, no recommendation yet, just verify the data pipeline works.

## Before you write code

Produce a short task list / implementation plan first and pause for my review. Ask me directly if anything's ambiguous rather than assuming.

## Definition of done for this phase

- Repo runs locally with documented setup.
- `SPEC.md` and `data/regions.json` exist in the repo, matching what was pasted above.
- Running the CLI for a sample date prints real (not mocked) Open-Meteo data for all 12 regions × 3 tiers, with correct colors, in one batched API call.
- An out-of-range date is rejected/clamped with a clear message.
- The color rule engine and headline-peak lookup each have their own unit tests, independent of any network call.

Don't build agents, the Skill, or the report layout yet — that's Phase 2 and Phase 3.
