# GoNoGo — How to Start in Antigravity

Everything you need is below and in the 5 attached files. You shouldn't need to scroll back through the chat that produced these.

## Project name

**GoNoGo** — the real name now, not a placeholder; named after the core decision rule the product is built around ("one red cell anywhere and I skip that region"). You went back and forth on this (briefly tried WeatherWindow as a safer placeholder, then decided to keep GoNoGo and protect it via copyright/licensing instead — see below). Already baked into `SPEC.md` and all phase files.

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

## Protecting the idea — what's actually in place now

A few things worth knowing (I'm not a lawyer — general practical orientation, not legal advice):

- **You've kept the name GoNoGo.** Domain being free is a weak signal for trademark safety — it's a different system entirely. Before treating the name as commercially safe, do the free checks yourself: a USPTO TESS search, and a quick look at the App Store/Google Play for existing "go no go" apps. "Go/No-Go" is a generic phrase used across many industries, which cuts two ways: harder to get a strong *exclusive* trademark on it later, but also lower odds someone's already locked it down in exactly your space.
- **Copyright is now explicit in `SPEC.md` and gets written into the repo in Phase 1**: a `LICENSE` file (all-rights-reserved by default, not MIT/Apache) plus a copyright line in the README. Public repo ≠ open-source license — people can read it for capstone evaluation without being legally free to reuse it commercially.
- **Competition IP terms — verified, corrected from my earlier guess**: Winner License Type is **CC-BY 4.0** (Sections 1.6/2.5 of the actual rules). This only triggers if you **win** one of the 12 swag prizes (3 per category) — then your winning submission + source code must be licensed CC-BY 4.0 (open, commercial use explicitly allowed, attribution required). You keep your own ownership either way; CC-BY just adds a public license on top. You can decline a win within a week of the deadline if you'd rather keep full exclusivity instead. If you don't win, this never applies.
- **Separate, smaller point**: if you post code snippets on the Kaggle competition's own discussion forum/notebooks during the event (not your GitHub repo, specifically Kaggle's forum), that's treated as "Public Code Sharing" and is automatically deemed open-source licensed too. Doesn't affect a GitHub repo you just link to from your writeup — just worth knowing before pasting code directly into Kaggle's forum.
- **The real moat is still execution + the curated data**, not secrecy — worth re-reading if you find yourself tempted to hide more of the plan than is useful for getting a good capstone score.
