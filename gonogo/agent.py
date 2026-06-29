# © 2026 Nataliya Zhuravleva. All rights reserved.
import os
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps import App
from google.adk.events import Event

from gonogo.app_utils.telemetry import StructuredLoggingPlugin


class MockRootAgent(BaseAgent):
    """Mock agent for integration testing to prevent live API calls and date parsing errors."""

    def __init__(self, name: str = "root_agent"):
        super().__init__(
            name=name, description="Mock root agent for integration testing"
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        from google.genai import types

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="Hello! This is a mock integration test response."
                    )
                ],
            ),
        )


if os.environ.get("INTEGRATION_TEST") == "TRUE":
    root_agent = MockRootAgent()
else:
    from gonogo.agents import OrchestratorAgent

    root_agent = OrchestratorAgent()

app = App(
    root_agent=root_agent,
    name="gonogo",
    plugins=[StructuredLoggingPlugin()],
)
