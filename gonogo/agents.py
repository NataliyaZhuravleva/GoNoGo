# © 2026 Nataliya Zhuravleva. All rights reserved.
import os
import re
from collections.abc import AsyncGenerator
from datetime import date

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from typing_extensions import override

from gonogo.core import fetch_conditions, validate_and_clamp_date_range


class ConditionsAgent(BaseAgent):
    """Deterministic agent that fetches weather conditions. Makes zero LLM calls."""

    def __init__(self, name: str = "conditions_agent"):
        super().__init__(
            name=name,
            description="Fetches weather forecast data for the 12 PNW regions.",
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Retrieve parsed dates from state
        start_date_str = ctx.session.state.get("start_date")
        end_date_str = ctx.session.state.get("end_date")

        if not start_date_str or not end_date_str:
            raise ValueError("Start date and end date must be set in session state.")

        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)

        # Fetch weather conditions from Open-Meteo
        forecasts = fetch_conditions(start_date, end_date)

        # Tool-injection guardrail: serialize to raw dictionaries using Pydantic validation
        # to ensure the weather response maps strictly to the schema (no instruction injection).
        serialized_forecasts = [f.model_dump() for f in forecasts]

        ctx.session.state["forecast_data"] = serialized_forecasts

        # Yield the state delta so it gets persisted in the session service
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"forecast_data": serialized_forecasts}),
        )


class AdvisorAgentFactory:
    """Helper to load the skill and instantiate the LLM-backed Advisor Agent."""

    @staticmethod
    def create(name: str = "advisor_agent") -> Agent:
        # Load local skill package
        skills_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "skills",
            "mountaineering-conditions-skill",
        )

        if not os.path.exists(skills_dir):
            raise FileNotFoundError(f"Skill directory not found at {skills_dir}")

        skill = load_skill_from_dir(skills_dir)
        skill_toolset = SkillToolset(skills=[skill])

        # Advisor instruction with dynamic state injection placeholder
        instruction = (
            "You are an expert Pacific Northwest (PNW) mountaineering advisor. Your job is to analyze weather conditions "
            "across 12 regions and provide conditions notes and top recommendations.\n\n"
            "Here is the weather forecast data for the requested date range:\n"
            "{forecast_data_summary}\n\n"
            'You MUST use the `load_skill` tool with skill_name="mountaineering-conditions-skill" to read and load the '
            "mountaineering domain knowledge and rules regarding wind thresholds, freezing level elevation hazards (freeze-thaw "
            "and rockfall), precipitation types (rain vs. snow hazards), and visibility/whiteout hazards. DO NOT skip this step.\n\n"
            "Based on the data and the skill guidelines, write:\n"
            "1. A short, professional conditions note (1-2 sentences) for each of the 12 regions. Focus on specific hazards "
            "relevant to mountaineers (e.g. warm freezing levels relative to peak, exposed high winds, rain on snow, or low visibility "
            "whiteout risk).\n"
            "2. One top overall recommendation specifying the best region (and day, if a range was selected) to climb, with "
            "a clear, convincing rationale.\n\n"
            "You MUST return your response in the following JSON format inside a markdown json code block:\n"
            "```json\n"
            "{\n"
            '  "top_recommendation": "...",\n'
            '  "region_notes": {\n'
            '    "baker_shuksan": "...",\n'
            '    "washington_pass": "...",\n'
            "    ...\n"
            "  }\n"
            "}\n"
            "```"
        )

        return Agent(
            name=name,
            model="gemini-2.5-flash",
            instruction=instruction,
            tools=[skill_toolset],
        )


class OrchestratorAgent(BaseAgent):
    """Workflow agent that validates inputs, runs sub-agents in sequence, and outputs final verdicts."""

    def __init__(self, name: str = "orchestrator_agent"):
        cond = ConditionsAgent()
        adv = AdvisorAgentFactory.create()
        super().__init__(
            name=name,
            description="Coordinates Conditions fetching and Advisor evaluations.",
            sub_agents=[cond, adv],
        )
        self._conditions_agent = cond
        self._advisor_agent = adv

    def _format_forecast_for_advisor(self, forecast_data: list[dict]) -> str:
        """Formats raw forecast data into a compact text block for the LLM context."""
        lines = []
        for reg in forecast_data:
            lines.append(
                f"Region: {reg['region_name']} (ID: {reg['region_id']}, Headline Peak: {reg['headline_peak_name']})"
            )
            past_precip_in = reg["past_48h_precip_mm"] / 25.4
            lines.append(f"Past 48h Precipitation: {past_precip_in:.2f} inches")
            for tier_key in ["base", "mid", "peak"]:
                tier = reg["tiers"][tier_key]
                lines.append(
                    f"  - {tier['tier_name']} Tier ({int(tier['elevation_ft'])} ft) - Worst Color Verdict: {tier['composite_color']}"
                )
                for day in tier["forecast_days"]:
                    date_str = day["date"]
                    m = day["parts"]["morning"]
                    d = day["parts"]["midday"]
                    e = day["parts"]["evening"]

                    lines.append(f"    * Date: {date_str}")
                    lines.append(
                        f"      Morning: Wind={m['wind']['reason']}, Precip={m['precipitation']['reason']}, "
                        f"Freezing={m['freezing_level']['reason']}, Vis={m['visibility']['reason']}, Cloud={m['cloud_cover']['reason']}. "
                        f"Verdict: {m['composite_color']}"
                    )
                    lines.append(
                        f"      Midday: Wind={d['wind']['reason']}, Precip={d['precipitation']['reason']}, "
                        f"Freezing={d['freezing_level']['reason']}, Vis={d['visibility']['reason']}, Cloud={d['cloud_cover']['reason']}. "
                        f"Verdict: {d['composite_color']}"
                    )
                    lines.append(
                        f"      Evening: Wind={e['wind']['reason']}, Precip={e['precipitation']['reason']}, "
                        f"Freezing={e['freezing_level']['reason']}, Vis={e['visibility']['reason']}, Cloud={e['cloud_cover']['reason']}. "
                        f"Verdict: {e['composite_color']}"
                    )
            lines.append("-" * 60)
        return "\n".join(lines)

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_query = ctx.user_content.parts[0].text.strip()

        # Parse query for dates if present
        parts = [p.strip() for p in user_query.replace("to", " ").split() if p.strip()]

        has_date = False
        if parts:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0]):
                has_date = True

        if has_date:
            start_date_str = parts[0]
            end_date_str = (
                parts[1]
                if (len(parts) > 1 and re.match(r"^\d{4}-\d{2}-\d{2}$", parts[1]))
                else None
            )
            start_date, end_date, warning = validate_and_clamp_date_range(
                start_date_str, end_date_str
            )
        else:
            from datetime import timedelta

            today = date.today()
            start_date = today + timedelta(days=1)
            end_date = start_date + timedelta(days=6)
            warning = None

        if warning:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"Warning: {warning}")],
                ),
            )

        # Store dates in state for ConditionsAgent
        ctx.session.state["start_date"] = start_date.isoformat()
        ctx.session.state["end_date"] = end_date.isoformat()

        # Step 2: Trigger ConditionsAgent (Deterministic)
        async with Aclosing(self._conditions_agent.run_async(ctx)) as agen:
            async for event in agen:
                yield event

        # Read weather data populated by ConditionsAgent
        forecast_data = ctx.session.state.get("forecast_data")
        if not forecast_data:
            raise ValueError("ConditionsAgent failed to populate forecast data.")

        # Format the weather data summary
        forecast_summary = self._format_forecast_for_advisor(forecast_data)

        # Inject the summary into the session state for AdvisorAgent's instruction
        ctx.session.state["forecast_data_summary"] = forecast_summary

        # Step 3: Trigger AdvisorAgent (LLM-based)
        # Yield the progress update
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="[System] Generating regional advisor notes..."
                    )
                ],
            ),
        )

        async with Aclosing(self._advisor_agent.run_async(ctx)) as agen:
            async for event in agen:
                yield event
