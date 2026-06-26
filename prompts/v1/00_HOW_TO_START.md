# GoNoGo — How to Start in Antigravity

Everything you need is below and in the 5 attached files. You shouldn't need to scroll back through the chat that produced these.

## Project name

**GoNoGo** — from the core decision rule the product is built around: scan the board, if there's a red cell anywhere for a region, skip it; go where everything's green. Already baked into `SPEC.md` and all phase files.

## The 5 files

| File | What it is | What you do with it |
|---|---|---|
| `SPEC.md` | The permanent project spec — context, product concept, scope, data model, architecture, agent design, dashboard design, guardrails. | Paste once, inside Phase 1's message. Antigravity saves it into the repo. Never re-paste after that — it just re-reads it from disk. |
| `regions.json` | The actual data: 12 PNW regions, their peaks, the headline peak per region, and real-sourced base/mid/peak elevations in feet. | Paste once, inside Phase 1's message, right after SPEC.md. Antigravity saves it as `data/regions.json`. |
| `phase1_setup_and_core.md` | First message to Antigravity. Scaffolds the repo, saves the two files above, builds the deterministic Open-Meteo fetch tool + color rule engine. No agents, no Gemini calls yet. | Copy its full contents into Antigravity as your very first message. |
| `phase2_agents_and_skill.md` | Second message. Builds the Orchestrator/Conditions/Advisor agents and the `mountaineering-conditions-skill`. | Copy into Antigravity **after** Phase 1 is done and you're happy with it. |
| `phase3_report_and_polish.md` | Third message. Assembles the full report (top recommendation + 12 regions north→south + 3 tier-tables each), plus the remaining guardrails/eval/logging. | Copy into Antigravity **after** Phase 2 is done. |

## Step by step

1. Open `phase1_setup_and_core.md`. Where it says `[PASTE THE FULL CONTENTS OF SPEC.md HERE]`, replace that line with the entire contents of `SPEC.md`. Where it says `[PASTE THE FULL CONTENTS OF regions.json HERE]`, replace that line with the entire contents of `regions.json`.
2. Paste the whole resulting message into Antigravity as your first message for a new project.
3. Antigravity should respond with a task list / implementation plan first (the prompt asks for this) — review it, then let it proceed.
4. Check the Phase 1 "Definition of done" checklist (at the bottom of `phase1_setup_and_core.md`) against what got built. If something's off, say so before moving on — don't let a wrong foundation carry into Phase 2.
5. Once Phase 1 looks right: copy the full contents of `phase2_agents_and_skill.md` as your next message, as-is (no pasting needed — Antigravity already has `SPEC.md` in the repo and will re-read it).
6. Check Phase 2's done-checklist, then do the same with `phase3_report_and_polish.md`.

## Things worth remembering going in

- **Model choice for cost**: default to a **Flash** model for the Advisor agent, not Pro — Pro models are paid-only now, Flash still has a free tier and this task (writing short notes from structured data) doesn't need a frontier model. Only reach for Pro if the notes come out too generic.
- **Your `GOOGLE_API_KEY`** goes in `.env`, never hardcoded — both phase prompts already say this, just don't paste the actual key into Antigravity's chat.
- **Set a budget alert** (e.g. $5) in Google Cloud Billing → Budgets & Alerts, so you get a warning before your $10 runs out, especially once you start experimenting with models/calls beyond what the spec calls for.
- **One Gemini call per report, not per region** — if at any point you notice Antigravity building something that calls Gemini 12 times (once per region) instead of once in a single batched call, that's a deviation from the spec worth catching early.
- **Don't let it jump ahead** — each phase file explicitly scopes out what NOT to build yet (e.g., Phase 1 says no agents). If Antigravity's plan includes something from a later phase, that's fine to notice and just say "let's hold that for Phase 2/3."
