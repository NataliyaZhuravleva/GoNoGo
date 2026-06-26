# SPEC.md — GoNoGo (PNW Mountaineering Conditions Board)

> This is the living spec for **GoNoGo**, the project name. Antigravity should save this file verbatim into the repo root on Phase 1, and treat it as the source of truth across phases — re-read it instead of expecting it to be re-pasted every message.

## Context

**Project name: GoNoGo** — named after the core decision rule the whole product is built around ("one red cell anywhere and I skip that region"). Capstone project for Google & Kaggle's "AI Agents: Intensive Vibe Coding" course, targeting the **Concierge Agents** category. The rubric rewards agentic reasoning and tool use, not just a data dashboard. Model: Gemini API, key in `GOOGLE_API_KEY` env var (Google AI Studio). Dev environment: Antigravity.

## Product concept

A toorainy-style mountaineering conditions board for the Pacific Northwest. The board automatically displays a weekly conditions report (7 days starting tomorrow) covering **all 12 regions at once**, sorted north to south, each with a short agent-written note and a 3-tier (base/mid/peak elevation) conditions table. A single best-overall recommendation is pinned at the top. No personalization, no preference questions.

Page structure, top to bottom:
1. **Top recommendation** — one sentence naming the best region and day with a short reason.
2. **12 regions, north to south** — region name, short agent-written note, base/mid/peak conditions table.

## MVP scope — IN

- Mountaineering only (no rock/ice climbing, ski touring, biking yet — but keep `activity_tags` extensible).
- Fixed 12 PNW regions (see `data/regions.json`), always shown all at once, sorted north→south by latitude.
- Input: None required. A single button allows refreshing the weekly board.
- Each region's weather = its **single highest peak** ("headline peak") at **3 elevation tiers: base, mid, peak**. No cross-peak averaging — see `data/regions.json`'s `tiers` field, already computed from real trailhead/camp research.
- Weather source: **Open-Meteo** (`https://api.open-meteo.com/v1/forecast`), free, no key, supports multi-location batched requests via comma-separated coordinates.
- Agent writes a short note per region + one top recommendation, generated from structured tier data (no preferences to weigh).

## MVP scope — OUT (don't build, but don't block later)

- Free-text chat interface or interactive query inputs.
- Peak-level drill-down UI (data already supports it via the `peaks` array, just not exposed as a screen).
- External trip-report pulling (WTA/AllTrails/Mountain Project) — leave room via future `routes`/`external_ids` fields.
- Persistent cross-session memory.
- Anything beyond a CLI/notebook test harness.
- Cloud deployment, automated red-teaming.

## Data model

Elevations in **feet**. Lat/lon in decimal degrees. Full data lives in `data/regions.json` (12 regions, each with `peaks[]`, `headline_peak_id`, and a `tiers` object with real-sourced `base`/`mid`/`peak` elevations — already researched, don't re-derive). Each peak that is the headline also carries `"is_headline": true` inline for easy scanning.

**Why this matters**: don't average peak coordinates (a virtual centroid isn't real terrain — bad for wind especially). Don't derive base/mid from a flat offset formula (breaks badly on big-relief mountains — verified on Rainier). `tiers.base`/`tiers.mid` are either a real named trailhead/camp (`source: "named_trailhead"` / `"named_camp"`) or, where no dominant camp exists, an honest midpoint between real trailhead and summit (`source: "midpoint"`) — never a placeholder formula.

Batch all 12 regions × 3 tiers (36 coordinate-elevation pairs) into **one** Open-Meteo request — stays cheap as more peaks/regions get added later.

Known limitation: reusing a peak's own lat/lon with a different `elevation` param per tier mainly adjusts temperature via lapse rate; wind/precip/cloud-cover aren't precisely altitude-corrected this way. Accepted MVP simplification.

## Copyright & licensing

`© 2026 [your name/handle]. All rights reserved.` — add this line to the README and as a header comment in key source files.

Important nuance: **a public repo is not the same as an open-source license.** Visibility (anyone can read/clone it for the capstone evaluation) and reuse rights (whether anyone else can legally copy/modify/redistribute it) are separate things. If no `LICENSE` file is added, standard copyright applies by default — the code is visible, but not legally free for others to reuse commercially. Don't add an MIT/Apache-style permissive license unless you actually want to allow that.

If you want to be extra explicit (recommended, since intent matters in disputes), add a one-line `LICENSE` file:

```
Copyright (c) 2026 [your name/handle]

All rights reserved. This code is shared publicly for the Kaggle/Google
AI Agents Intensive capstone evaluation only. No license is granted for
reuse, modification, or redistribution without the author's permission.
```

**Verified from the actual competition rules** (Vibecoding Agents - Capstone Project, Section 1.6 / 2.5): this only matters if you **win**. Winner License Type is **CC-BY 4.0** — if selected as one of the 12 swag winners (3 per category, including Concierge Agents), you must license your winning submission and its source code under CC-BY 4.0, which explicitly permits commercial use by anyone, with attribution. This does not strip your ownership — you keep your copyright and can still build a business on your own code; it just means the public also gets a license, with attribution. You can decline a win (and avoid this obligation) within one week of the Final Submission Deadline if you'd rather keep full exclusivity (Foundational Rules Section 3.8.b). If you don't win, none of this applies, and the copyright/LICENSE-file approach above stands as-is.



- **Agentic pattern**: tool/function calling to fetch weather — agent decides what to fetch, not static context dump.
- **Use Google ADK**, not raw `google-genai` SDK calls — the course covered ADK multi-agent patterns and Skills; this capstone should demonstrate them. Use ADK's session/state service (keep door open for future per-user memory). Use `agents-cli` to scaffold if Antigravity has it.
- **Multi-agent, but not every sub-agent needs to be LLM-backed.** Only use the model where real reasoning/generation happens. Deterministic steps (fetching, coloring) should stay plain code or non-LLM ADK agents — intentional, keeps cost down.
- **Skills**: at least one real ADK Agent Skill, loaded on demand, not pasted into every system prompt.
- **Language**: Python 3.11+.
- **Cost-consciousness**: Open-Meteo fetch is one batched call (36 points). Advisor's notes+recommendation is **one** batched Gemini call covering all 12 regions, not 12 separate calls. No speculative looping, no background polling.

## Agent architecture (multi-agent + skill)

1. **Orchestrator** (root, workflow/Sequential controller — doesn't need to be LLM-backed) — triggers Conditions then Advisor in sequence, sorts output north→south, places top recommendation above the list.
2. **Conditions agent** (deterministic, no LLM) — owns the Open-Meteo tool. For each region's `headline_peak_id`, builds 3 coordinate-elevation pairs from `tiers`, batches all 12×3=36 into one request, returns structured per-region-per-tier data. No reasoning, no coloring, no cross-peak averaging.
3. **Advisor agent** (this is where LLM reasoning happens) — receives all 12 regions' tier data + the deterministic color verdicts (see Overview dashboard), produces in **one batched call**: a short note per region + the single top-pick recommendation with a short reason. No preferences to weigh — synthesis of data, not personalized ranking. Loads the Skill below.

**Skill**: `mountaineering-conditions-skill` — domain knowledge for turning raw numbers into climbing-relevant judgment:
- Wind thresholds that matter on exposed ridges/summits vs. sheltered approaches.
- Why freezing level relative to peak elevation matters more than raw temperature (snow/ice conditions, freeze-thaw rockfall).
- Why precipitation *type* matters more than amount for route conditions.
- How cloud cover/visibility affects navigation risk independent of temperature.

Package this as a real ADK Skill (its own file/package with instructions + metadata), loaded by the Advisor agent on demand — not pasted into every system prompt. Look up the exact ADK Skill packaging convention if unsure rather than guessing.

## Overview dashboard (toorainy-style, 3-tier) — the only screen in this MVP

Modeled on toorainy.com: show every region at once, no single-region drill-in first. Only control is a Refresh button.

1. **Top recommendation** pinned above everything.
2. **12 regions, north→south.** Each: name, short Advisor note, three stacked tables (**base/mid/peak**). Each tier-table: next 7 days × 3 day-parts (morning/midday/evening) = 21 columns, composite green/yellow/red cell.
3. **Overall column per region per tier**: worst color among that tier-table's visible cells — implements "one red cell and I skip it."
4. **Region-level badge**: precipitation in the last 48h (Open-Meteo `past_days`), once per region.

**Cell coloring is deterministic, never LLM-driven** — plain Python rule engine using the Skill's thresholds, not a model call per cell (12×3×9=324 cells). The Advisor's one batched call covers only the notes and the top pick.

Rendering can stay simple (clean text/markdown) until a later phase — a real date-picker widget and polished web UI are deliberately deferred.

## Quality, security & observability (lightweight, build progressively across phases)

- **7-day weekly horizon**: automatically defaults to a 7-day range starting tomorrow, aligned to Open-Meteo's reliable forecast horizon.
- **Scope guardrail**: all peak/region computation comes strictly from `data/regions.json`.
- **Tool-output injection guardrail**: Conditions and Advisor agents both treat Open-Meteo responses as untrusted data, never instructions.
- **Lightweight eval**: 3-5 hardcoded golden scenarios (mocked weather → obviously-correct expected outcome), no live API/model calls needed.
- **Observability**: structured JSON-lines logging per agent step (which agent, which tool, summary, latency).
- **Explicitly NOT in scope**: cloud deployment, comprehensive red-teaming, persistent cross-session memory — note as "future work" in README, don't build.

## Overall definition of done (full project, checked progressively across phases)

- Project runs locally with documented setup.
- Running the app produces a full weekly report (top rec + 12 regions north→south, notes, 3 tier-tables) — real Open-Meteo data, real agent pipeline (Orchestrator → Conditions → Advisor), not mocked or monolithic.
- Advisor notes visibly reflect the Skill's content (mention freezing level/wind exposure, not generic "sunny/not sunny").
- Golden-set eval passes without live API/model calls (or a small fixed number).
- Log file shows per-agent, per-tool trace after a run.
- Headline-peak selection (max elevation per region) is a tested pure function.
- Color rule engine has its own unit tests, independent of any agent call.
- Adding a new region/peak/data source later doesn't require rewriting the orchestrator.
