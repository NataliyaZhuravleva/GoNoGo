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

from dotenv import load_dotenv
load_dotenv(override=True)

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
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --card-hover-border: rgba(0, 188, 212, 0.4);
            --border-color: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --accent-primary: #00bcd4;
            --accent-secondary: #0097a7;
            
            --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --shadow-hover: 0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.08);
            --shadow-glow: 0 10px 25px rgba(0, 188, 212, 0.08);
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
                radial-gradient(at 0% 0%, rgba(0, 188, 212, 0.04) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(0, 151, 167, 0.04) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 1.5rem;
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
            margin-bottom: 0.75rem;
        }

        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary), #00e5ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
            letter-spacing: -0.03em;
        }

        header p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 300;
        }

        /* Controls */
        .controls-card {
            background: transparent;
            border: none;
            padding: 0;
            margin-bottom: 1rem;
            display: flex;
            justify-content: center;
            box-shadow: none;
        }

        .btn-submit {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border: none;
            border-radius: 12px;
            padding: 0.25rem 0.75rem;
            color: white;
            font-family: inherit;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 6px -1px rgba(0, 188, 212, 0.15);
        }

        .btn-submit:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 10px -3px rgba(0, 188, 212, 0.25);
        }

        .btn-submit:active {
            transform: translateY(0);
        }

        /* Top Recommendation */
        .recommendation-card {
            background: linear-gradient(135deg, rgba(0, 188, 212, 0.04), rgba(0, 151, 167, 0.04));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 151, 167, 0.15);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-glow);
            display: none;
            animation: slideUp 0.5s ease-out;
        }

        .rec-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            color: var(--accent-primary);
        }

        .rec-text {
            font-size: 1rem;
            line-height: 1.5;
            color: var(--text-primary);
            font-weight: 400;
        }

        /* Region Cards Grid */
        .regions-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        .region-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: var(--shadow-card);
            transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
            animation: fadeIn 0.5s ease-out;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .region-card:hover {
            border-color: var(--card-hover-border);
            transform: translateY(-1px);
            box-shadow: var(--shadow-hover);
        }

        .region-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 0.75rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
        }

        .region-title-area {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .region-name {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .region-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .badge-rain {
            background: rgba(0, 188, 212, 0.08);
            border: 1px solid rgba(0, 188, 212, 0.15);
            color: var(--accent-primary);
            border-radius: 99px;
            padding: 0.25rem 0.75rem;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }

        .region-note {
            background: rgba(0, 0, 0, 0.015);
            border-left: 4px solid var(--accent-primary);
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.95rem;
            line-height: 1.4;
            color: #334155;
        }

        /* 3-Tier Tables */
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background: #ffffff;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.85rem;
            min-width: 880px;
            table-layout: fixed;
        }

        th, td {
            padding: 0.4rem 0.4rem;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background: #f8fafc;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
        }

        td.tier-label {
            font-weight: 600;
            color: var(--text-primary);
            background: #f8fafc;
            border-right: 2px solid var(--border-color);
            font-size: 0.8rem;
            width: 140px;
            min-width: 140px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Day part rendering */
        .day-column-cell {
            text-align: center;
        }

        .dot-cell {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            display: inline-block;
            position: relative;
            vertical-align: middle;
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
            font-size: 0.8rem;
            vertical-align: middle;
        }

        .bg-green { background-color: #d1fae5; border: 1.5px solid #10b981; }
        .bg-yellow { background-color: #fef3c7; border: 1.5px solid #f59e0b; }
        .bg-red { background-color: #fee2e2; border: 1.5px solid #ef4444; }

        .overall-badge.bg-green { color: #065f46; }
        .overall-badge.bg-yellow { color: #78350f; }
        .overall-badge.bg-red { color: #991b1b; }

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
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0, 188, 212, 0.1);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        .message-box {
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #b91c1c;
            padding: 1.25rem;
            border-radius: 12px;
            margin-bottom: 2rem;
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
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Tooltip style */
        .dot-cell::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(-6px);
            background: #1e293b;
            color: #fff;
            padding: 0.45rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 400;
            width: max-content;
            max-width: 250px;
            white-space: normal;
            word-wrap: break-word;
            line-height: 1.4;
            text-align: left;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.15s;
            z-index: 10;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
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
        <div class="controls-card">
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

            const getTooltipText = (partLabel, timeRange, partData) => {
                let issues = [];
                const metrics = ["wind", "precipitation", "freezing_level", "visibility", "cloud_cover"];
                metrics.forEach(k => {
                    const met = partData[k];
                    if (met && met.color !== "Green") {
                        const formattedLabel = k.charAt(0).toUpperCase() + k.slice(1).replace('_', ' ');
                        issues.push(`${formattedLabel}: ${met.reason}`);
                    }
                });
                
                if (issues.length === 0) {
                    return `${partLabel} (${timeRange}): Green - Safe conditions`;
                }
                
                return `${partLabel} (${timeRange}): ${partData.composite_color} - ${issues.join("; ")}`;
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
                        let headerRow1 = `<th rowspan="3" style="vertical-align: middle; border-right: 2px solid var(--border-color); width: 140px; min-width: 140px;">Tiers</th>`;
                        let headerRow2 = ``;
                        let headerRow3 = ``;
                        
                        datesList.forEach(dt => {
                            const parts = dt.split("-");
                            const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
                            const dayOfWeek = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                            const dayOfMonth = parts[2];
                            
                            headerRow1 += `<th colspan="3" style="text-align: center; border-right: 2px solid var(--border-color);">${dayOfWeek}</th>`;
                            headerRow2 += `<th colspan="3" style="text-align: center; border-bottom: 1px solid var(--border-color); border-right: 2px solid var(--border-color); font-size: 0.8rem; font-weight: 500;">${dayOfMonth}</th>`;
                            headerRow3 += `
                                <th style="text-align: center; font-size: 0.65rem; font-weight: 600; padding: 0.25rem 0.15rem; width: 35px; min-width: 35px; max-width: 35px;">AM</th>
                                <th style="text-align: center; font-size: 0.65rem; font-weight: 600; padding: 0.25rem 0.15rem; width: 35px; min-width: 35px; max-width: 35px;">PM</th>
                                <th style="text-align: center; font-size: 0.65rem; font-weight: 600; padding: 0.25rem 0.15rem; width: 35px; min-width: 35px; max-width: 35px; border-right: 2px solid var(--border-color);">Night</th>
                            `;
                        });

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
                                    <td style="text-align: center; padding: 0.4rem 0.25rem; width: 35px; min-width: 35px; max-width: 35px;">
                                        <span class="dot-cell ${colorClassMap[m.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="${getTooltipText('AM', '4am-12pm', m)}"></span>
                                    </td>
                                    <td style="text-align: center; padding: 0.4rem 0.25rem; width: 35px; min-width: 35px; max-width: 35px;">
                                        <span class="dot-cell ${colorClassMap[d.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="${getTooltipText('PM', '12pm-8pm', d)}"></span>
                                    </td>
                                    <td style="text-align: center; padding: 0.4rem 0.25rem; width: 35px; min-width: 35px; max-width: 35px; border-right: 2px solid var(--border-color);">
                                        <span class="dot-cell ${colorClassMap[e.composite_color.toLowerCase()] || "bg-red"}" data-tooltip="${getTooltipText('Night', '8pm-4am', e)}"></span>
                                    </td>
                                `;
                            });

                            tableRows += `
                                <tr>
                                    <td class="tier-label">${tierObj.label}</td>
                                    ${cells}
                                </tr>
                            `;
                        });

                        card.innerHTML = `
                            <div class="region-header">
                                <div class="region-title-area">
                                    <div class="region-name">${reg.headline_peak_name}</div>
                                    <div class="region-meta">${reg.region_name}</div>
                                </div>
                            </div>
                            <div class="region-note">
                                ${note}
                            </div>
                            <div class="table-container">
                                <table>
                                    <thead>
                                        <tr>${headerRow1}</tr>
                                        <tr>${headerRow2}</tr>
                                        <tr>${headerRow3}</tr>
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
