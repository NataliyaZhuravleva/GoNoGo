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
import os
import logging as std_logging

import google.auth
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from google.adk.cli.fast_api import get_fast_api_app

from gonogo.app_utils.telemetry import setup_telemetry
from gonogo.app_utils.typing import Feedback

setup_telemetry()

# Fallback logger for local / testing environments
class FallbackLogger:
    def __init__(self, name):
        self.name = name
    def log_struct(self, data: dict, severity: str = "INFO"):
        std_logging.info(f"[{severity}] Struct log: {data}")

# Attempt to load Google Cloud Logging, fallback to stdout logger if unavailable
try:
    if os.environ.get("INTEGRATION_TEST") == "TRUE":
        raise RuntimeError("Forced fallback for integration testing")
    from google.cloud import logging as google_cloud_logging
    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception as e:
    std_logging.warning(f"Google Cloud Logging initialization failed, using fallback: {e}")
    logger = FallbackLogger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "gonogo"
app.description = "API for interacting with the Agent gonogo"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


@app.get("/api/report")
async def get_report(start_date: str | None = None, end_date: str | None = None):
    """Run the multi-agent Orchestrator pipeline and return the report in JSON format."""
    try:
        from datetime import date, timedelta
        from gonogo.agents import OrchestratorAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        import re
        import json
        
        if not start_date:
            today = date.today()
            start_date = (today + timedelta(days=1)).isoformat()
            end_date = (today + timedelta(days=7)).isoformat()
            
        orchestrator = OrchestratorAgent()
        session_service = InMemorySessionService()
        user_id = "web-user"
        session_id = f"web-session-{start_date}"
        await session_service.create_session(app_name="gonogo", user_id=user_id, session_id=session_id)
        
        # We pass the StructuredLoggingPlugin as well so web runs are also logged
        from gonogo.app_utils.telemetry import StructuredLoggingPlugin
        runner = Runner(
            agent=orchestrator,
            app_name="gonogo",
            session_service=session_service,
            plugins=[StructuredLoggingPlugin()]
        )
        
        query = start_date
        if end_date:
            query += f" to {end_date}"
            
        final_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)])
        ):
            if event.author == "advisor_agent" and event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
                
        if not final_text:
            raise ValueError("Advisor failed to produce a final response.")
            
        json_content = final_text.strip()
        match = re.search(r"```json\s*(.*?)\s*```", final_text, re.DOTALL)
        if match:
            json_content = match.group(1).strip()
            
        report_data = json.loads(json_content)
        
        # Load session state to retrieve forecast_data
        session = await session_service.get_session(app_name="gonogo", user_id=user_id, session_id=session_id)
        forecast_data = session.state.get("forecast_data") if session else None
        
        return {
            "status": "success",
            "top_recommendation": report_data.get("top_recommendation"),
            "region_notes": report_data.get("region_notes"),
            "forecasts": forecast_data
        }
    except Exception as e:
        import traceback
        std_logging.error(f"Error generating report: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the premium dark-themed mountaineering conditions dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoNoGo — PNW Mountaineering Conditions Board</title>
    <meta name="description" content="Premium PNW mountaineering conditions board showing 3-tier elevation tables and automated Advisor notes.">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #080c14;
            --card-bg: rgba(17, 24, 39, 0.7);
            --card-hover-border: rgba(59, 130, 246, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-primary: #3b82f6;
            --accent-secondary: #8b5cf6;
            
            --color-green: #10b981;
            --color-yellow: #f59e0b;
            --color-red: #ef4444;
            
            --shadow-glow: 0 0 25px rgba(59, 130, 246, 0.15);
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.1) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 3rem 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            width: 100%;
            max-width: 1200px;
        }

        /* Header */
        header {
            text-align: center;
            margin-bottom: 3rem;
        }

        h1 {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.05em;
        }

        header p {
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 300;
        }

        /* Controls / Form */
        .controls-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin-bottom: 2.5rem;
            display: flex;
            gap: 1.5rem;
            align-items: flex-end;
            flex-wrap: wrap;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
        }

        .input-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            flex: 1;
            min-width: 200px;
        }

        .input-group label {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .input-group input {
            background: rgba(31, 41, 55, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .input-group input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.25);
        }

        .btn-submit {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border: none;
            border-radius: 8px;
            padding: 0.75rem 2rem;
            color: white;
            font-family: inherit;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn-submit:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(139, 92, 246, 0.4);
        }

        .btn-submit:active {
            transform: translateY(0);
        }

        /* Top Recommendation */
        .recommendation-card {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 3rem;
            box-shadow: var(--shadow-glow);
            display: none;
            animation: slideUp 0.5s ease-out;
        }

        .rec-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.3rem;
            margin-bottom: 0.75rem;
            color: #60a5fa;
        }

        .rec-text {
            font-size: 1.15rem;
            line-height: 1.6;
            color: var(--text-primary);
            font-weight: 400;
        }

        /* Region Cards Grid */
        .regions-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2.5rem;
        }

        .region-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s, border-color 0.3s;
            animation: fadeIn 0.5s ease-out;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .region-card:hover {
            border-color: var(--card-hover-border);
            transform: translateY(-4px);
        }

        .region-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 1rem;
        }

        .region-title-area {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .region-name {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .region-meta {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .badge-rain {
            background: rgba(59, 130, 246, 0.2);
            border: 1px solid rgba(59, 130, 246, 0.4);
            color: #60a5fa;
            border-radius: 99px;
            padding: 0.35rem 0.85rem;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .region-note {
            background: rgba(255, 255, 255, 0.03);
            border-left: 4px solid var(--accent-primary);
            padding: 1rem 1.25rem;
            border-radius: 4px;
            font-size: 1rem;
            line-height: 1.5;
            color: #d1d5db;
        }

        /* 3-Tier Tables */
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
            min-width: 600px;
        }

        th, td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        th {
            background: rgba(31, 41, 55, 0.4);
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }

        td.tier-label {
            font-weight: 600;
            color: var(--text-primary);
        }

        /* Day part rendering */
        .day-column-cell {
            text-align: center;
        }

        .day-parts-dots {
            display: inline-flex;
            gap: 0.5rem;
            justify-content: center;
            align-items: center;
        }

        .dot-cell {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            position: relative;
        }

        /* Overall Badge */
        .overall-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 6px;
            font-weight: 700;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }

        .bg-green { background-color: var(--color-green); box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
        .bg-yellow { background-color: var(--color-yellow); box-shadow: 0 0 10px rgba(245, 158, 11, 0.4); }
        .bg-red { background-color: var(--color-red); box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }

        /* Loader & Messages */
        .loader-container {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 1.5rem;
            margin: 4rem 0;
            animation: fadeIn 0.3s ease-out;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .message-box {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2.5rem;
            display: none;
            line-height: 1.5;
            animation: fadeIn 0.3s ease-out;
            width: 100%;
        }

        /* Animations */
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Tooltip style */
        .dot-cell::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(-6px);
            background: rgba(0,0,0,0.85);
            color: #fff;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.15s;
            z-index: 10;
        }

        .dot-cell:hover::after {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>GoNoGo</h1>
            <p>Pacific Northwest Mountaineering Conditions Board</p>
        </header>

        <div class="message-box" id="error-message"></div>

        <!-- Date Range Controls -->
        <div class="controls-card" style="justify-content: center; align-items: center;">
            <button class="btn-submit" id="btn-fetch">Refresh Conditions</button>
        </div>

        <!-- Loading spinner -->
        <div class="loader-container" id="loader">
            <div class="spinner"></div>
            <p>Consulting conditions and interpreting mountaineering skill guidelines...</p>
        </div>

        <!-- Top Recommendation -->
        <div class="recommendation-card" id="recommendation-card">
            <div class="rec-header">
                🏆 Top Recommendation
            </div>
            <div class="rec-text" id="recommendation-text"></div>
        </div>

        <!-- Regions Container -->
        <div class="regions-grid" id="regions-container"></div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const fetchBtn = document.getElementById("btn-fetch");
            const loader = document.getElementById("loader");
            const errorMessage = document.getElementById("error-message");
            const recCard = document.getElementById("recommendation-card");
            const recText = document.getElementById("recommendation-text");
            const regionsContainer = document.getElementById("regions-container");

            const colorClassMap = {
                "green": "bg-green",
                "yellow": "bg-yellow",
                "red": "bg-red"
            };

            const getColorAbbr = (color) => {
                const c = color.toLowerCase();
                if (c === "green") return "G";
                if (c === "yellow") return "Y";
                return "R";
            };

            let isLoading = false;

            const loadReport = async () => {
                if (isLoading) return;
                isLoading = true;

                try {
                    // Clean UI
                    errorMessage.style.display = "none";
                    recCard.style.display = "none";
                    regionsContainer.innerHTML = "";
                    loader.style.display = "flex";

                    let url = `/api/report`;

                    const response = await fetch(url);
                    const data = await response.json();

                    loader.style.display = "none";

                    if (data.status === "error") {
                        showError(data.message);
                        return;
                    }

                    // Render Top Recommendation
                    if (data.top_recommendation) {
                        recText.textContent = data.top_recommendation;
                        recCard.style.display = "block";
                    }

                    // Render Regions
                    data.forecasts.forEach(reg => {
                        const note = data.region_notes[reg.region_id] || "No note generated.";
                        const card = document.createElement("div");
                        card.className = "region-card";

                        // Get dates list from first available tier
                        const peakTier = reg.tiers.peak;
                        const datesList = peakTier ? peakTier.forecast_days.map(d => d.date) : [];

                        // Build Table Header
                        let tableHeaders = `<th>Tiers</th>`;
                        datesList.forEach(dt => {
                            // format date to MM/DD
                            const parts = dt.split("-");
                            const formattedDate = `${parts[1]}/${parts[2]}`;
                            tableHeaders += `<th style="text-align: center;">${formattedDate}</th>`;
                        });
                        tableHeaders += `<th style="text-align: center;">Overall</th>`;

                        // Build Table Rows (Peak, Mid, Base)
                        let tableRows = "";
                        const tierOrder = [
                            { key: "peak", label: `Peak (${Math.round(reg.tiers.peak.elevation_ft)} ft)` },
                            { key: "mid", label: `Mid (${Math.round(reg.tiers.mid.elevation_ft)} ft)` },
                            { key: "base", label: `Base (${Math.round(reg.tiers.base.elevation_ft)} ft)` }
                        ];

                        tierOrder.forEach(tierObj => {
                            const tierData = reg.tiers[tierObj.key];
                            if (!tierData) return;

                            let cells = "";
                            tierData.forecast_days.forEach(day => {
                                const m = day.parts.morning;
                                const d = day.parts.midday;
                                const e = day.parts.evening;

                                cells += `
                                    <td class="day-column-cell">
                                        <div class="day-parts-dots">
                                            <span class="dot-cell ${colorClassMap[m.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="Morning: ${m.composite_color} - ${m.wind.reason}"></span>
                                            <span class="dot-cell ${colorClassMap[d.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="Midday: ${d.composite_color} - ${d.precipitation.reason}"></span>
                                            <span class="dot-cell ${colorClassMap[e.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="Evening: ${e.composite_color} - ${e.visibility.reason}"></span>
                                        </div>
                                    </td>
                                `;
                            });

                            const overallColor = tierData.composite_color.toLowerCase();
                            const overallClass = colorClassMap[overallColor] || "bg-red";
                            const overallText = getColorAbbr(overallColor);

                            tableRows += `
                                <tr>
                                    <td class="tier-label">${tierObj.label}</td>
                                    ${cells}
                                    <td style="text-align: center;">
                                        <span class="overall-badge ${overallClass}">${overallText}</span>
                                    </td>
                                </tr>
                            `;
                        });

                        card.innerHTML = `
                            <div class="region-header">
                                <div class="region-title-area">
                                    <div class="region-name">${reg.region_name}</div>
                                    <div class="region-meta">Headline Peak: ${reg.headline_peak_name}</div>
                                </div>
                                <div class="badge-rain">
                                    🌧️ ${reg.past_48h_precip_mm.toFixed(1)} mm <span style="font-size: 0.75rem; font-weight: 300;">(past 48h)</span>
                                </div>
                            </div>
                            <div class="region-note">
                                ${note}
                            </div>
                            <div class="table-container">
                                <table>
                                    <thead>
                                        <tr>${tableHeaders}</tr>
                                    </thead>
                                    <tbody>
                                        ${tableRows}
                                    </tbody>
                                </table>
                            </div>
                        `;
                        regionsContainer.appendChild(card);
                    });

                } catch (err) {
                    loader.style.display = "none";
                    showError("Failed to fetch forecast report. Make sure your server is running and your API key is correct.");
                    console.error(err);
                } finally {
                    isLoading = false;
                }
            };

            const showError = (msg) => {
                errorMessage.textContent = msg;
                errorMessage.style.display = "block";
            };

            fetchBtn.addEventListener("click", loadReport);
            
            // Auto load on open
            loadReport();
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
