# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry and GenAI telemetry with GCS upload."""

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    if bucket and capture_content != "false":
        logging.info(
            "Prompt-response logging enabled - mode: NO_CONTENT (metadata only, no prompts/responses)"
        )
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=gonogo,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logging.info(
            "Prompt-response logging disabled (set LOGS_BUCKET_NAME=gs://your-bucket and OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT to enable)"
        )

    return bucket


import time
import json
from typing import Any
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.base_agent import BaseAgent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext

class StructuredLoggingPlugin(BasePlugin):
    """Custom ADK Plugin that records agent and tool execution step traces to a JSONL file."""
    
    def __init__(self, log_path: str = "gonogo_runs.jsonl"):
        super().__init__(name="structured_logging")
        self.log_path = log_path
        self._start_times = {}  # key: (invocation_id, name) -> time

    def _write_log(self, record: dict):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logging.error(f"Failed to write structured log: {e}")

    # Agent Lifecycle Hooks
    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        inv_id = callback_context.invocation_id
        self._start_times[(inv_id, agent.name)] = time.perf_counter()
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        inv_id = callback_context.invocation_id
        start_time = self._start_times.pop((inv_id, agent.name), None)
        latency = time.perf_counter() - start_time if start_time else 0.0
        
        record = {
            "timestamp": time.time(),
            "type": "agent",
            "name": agent.name,
            "latency_sec": latency,
            "status": "success",
            "summary": f"Agent {agent.name} execution completed."
        }
        self._write_log(record)
        return None

    # Tool Lifecycle Hooks
    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> None:
        inv_id = tool_context.invocation_id
        self._start_times[(inv_id, tool.name)] = time.perf_counter()
        return None

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ) -> None:
        inv_id = tool_context.invocation_id
        start_time = self._start_times.pop((inv_id, tool.name), None)
        latency = time.perf_counter() - start_time if start_time else 0.0
        
        # Avoid logging potentially huge binary/payload content, keep it clean
        args_summary = {k: str(v)[:100] for k, v in tool_args.items()}
        record = {
            "timestamp": time.time(),
            "type": "tool",
            "name": tool.name,
            "latency_sec": latency,
            "status": "success",
            "summary": f"Tool {tool.name} invocation completed.",
            "args": args_summary
        }
        self._write_log(record)
        return None
