# © 2026 Nataliya Zhuravleva. All rights reserved.
import json
import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents.invocation_context import InvocationContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from gonogo.agents import ConditionsAgent, OrchestratorAgent
from gonogo.core import DailyForecast, DayParts, RegionForecast, TierForecast


@pytest.fixture
def mock_region_forecast():
    mock_verdict = {
        "composite_color": "Green",
        "wind": {"color": "Green", "reason": "Low wind"},
        "precipitation": {"color": "Green", "reason": "No precip"},
        "freezing_level": {"color": "Green", "reason": "Cold"},
        "visibility": {"color": "Green", "reason": "Clear"},
        "cloud_cover": {"color": "Green", "reason": "Clear"},
    }
    return RegionForecast(
        region_id="baker_shuksan",
        region_name="Mt. Baker / Mt. Shuksan",
        headline_peak_name="Mt. Baker",
        headline_peak_lat=48.7767,
        headline_peak_lon=-121.8144,
        past_48h_precip_mm=0.0,
        tiers={
            "base": TierForecast(
                tier_name="Base",
                elevation_ft=3000.0,
                forecast_days=[
                    DailyForecast(
                        date="2026-06-26",
                        parts=DayParts(
                            morning=mock_verdict,
                            midday=mock_verdict,
                            evening=mock_verdict,
                        ),
                    )
                ],
                composite_color="Green",
            ),
            "mid": TierForecast(
                tier_name="Mid",
                elevation_ft=6000.0,
                forecast_days=[
                    DailyForecast(
                        date="2026-06-26",
                        parts=DayParts(
                            morning=mock_verdict,
                            midday=mock_verdict,
                            evening=mock_verdict,
                        ),
                    )
                ],
                composite_color="Green",
            ),
            "peak": TierForecast(
                tier_name="Peak",
                elevation_ft=10000.0,
                forecast_days=[
                    DailyForecast(
                        date="2026-06-26",
                        parts=DayParts(
                            morning=mock_verdict,
                            midday=mock_verdict,
                            evening=mock_verdict,
                        ),
                    )
                ],
                composite_color="Green",
            ),
        },
    )


@pytest.mark.anyio
async def test_conditions_agent(mock_region_forecast):
    agent = ConditionsAgent()
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test", app_name="gonogo")
    session.state["start_date"] = "2026-06-26"
    session.state["end_date"] = "2026-06-26"

    ctx = InvocationContext(
        session_service=session_service,
        session=session,
        invocation_id="test-inv-1",
        user_content=types.Content(parts=[types.Part.from_text(text="")]),
    )

    with patch("gonogo.agents.fetch_conditions") as mock_fetch:
        mock_fetch.return_value = [mock_region_forecast]
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)

        assert len(events) == 1
        forecast_data = ctx.session.state.get("forecast_data")
        assert forecast_data is not None
        assert len(forecast_data) == 1
        assert forecast_data[0]["region_id"] == "baker_shuksan"


@pytest.mark.anyio
async def test_orchestrator_pipeline(mock_region_forecast):
    # Set dummy API key to pass Client initialization
    os.environ["GOOGLE_API_KEY"] = "dummy-api-key"

    orchestrator = OrchestratorAgent()
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="gonogo", user_id="user-1", session_id="sess-1"
    )

    runner = Runner(
        agent=orchestrator, app_name="gonogo", session_service=session_service
    )

    mock_llm_response = {
        "top_recommendation": "Snoqualmie Pass has the best composite weather conditions.",
        "region_notes": {
            "baker_shuksan": "Warm temps and clear skies.",
            "washington_pass": "Windy evening forecast.",
        },
    }

    # Mock the Client to return a mock response for LLM generate_content
    # Advisor agent runs in two steps:
    # 1st step: yields function call for load_skill
    # 2nd step: returns the markdown JSON code block
    async def mock_generate_content(*args, **kwargs):
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(
                                text=f"```json\n{json.dumps(mock_llm_response)}\n```"
                            )
                        ],
                    )
                )
            ]
        )

    # Patch both generate_content and generate_content_stream on a mock api_client
    async def mock_generate_content_stream(*args, **kwargs):
        response = await mock_generate_content(*args, **kwargs)
        yield response

    from unittest.mock import PropertyMock

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=mock_generate_content
    )
    mock_client.aio.models.generate_content_stream = mock_generate_content_stream

    with (
        patch("gonogo.agents.fetch_conditions") as mock_fetch,
        patch(
            "google.adk.models.google_llm.Gemini.api_client", new_callable=PropertyMock
        ) as mock_api_client_prop,
    ):
        mock_api_client_prop.return_value = mock_client
        mock_fetch.return_value = [mock_region_forecast]

        # Run orchestrator pipeline with a valid range
        events = []
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        day_after = (date.today() + timedelta(days=2)).isoformat()
        async for event in runner.run_async(
            user_id="user-1",
            session_id="sess-1",
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{tomorrow} to {day_after}")],
            ),
        ):
            events.append(event)

        assert len(events) > 0

        # Verify conditions were fetched and stored
        session = await session_service.get_session(
            app_name="gonogo", user_id="user-1", session_id="sess-1"
        )
        assert "forecast_data" in session.state
