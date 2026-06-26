# © 2026 Nataliya Zhuravleva. All rights reserved.
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date, timedelta

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from gonogo.agents import OrchestratorAgent
from gonogo.core import load_regions_data

# Load environment variables (such as GOOGLE_API_KEY)
load_dotenv()

# ANSI Escape Colors
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"

async def run_pipeline(start_date_str: str, end_date_str: str | None, use_color: bool):
    """Run the multi-agent Orchestrator pipeline and print results."""
    query = start_date_str
    if end_date_str:
        query += f" to {end_date_str}"
        
    print(f"[{COLOR_GREEN}System{COLOR_RESET if use_color else ''}] Initializing GoNoGo conditions check for: '{query}'...")
    
    # Check if GOOGLE_API_KEY is available
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print(
            f"[{COLOR_RED}Error{COLOR_RESET if use_color else ''}] Neither GOOGLE_API_KEY nor GEMINI_API_KEY is set in environment.\n"
            f"Please set your API key in the `.env` file in the project root.",
            file=sys.stderr
        )
        sys.exit(1)
        
    orchestrator = OrchestratorAgent()
    
    # Setup ADK session and runner
    session_service = InMemorySessionService()
    user_id = "user-default"
    session_id = "session-default"
    await session_service.create_session(app_name="gonogo", user_id=user_id, session_id=session_id)
    
    runner = Runner(agent=orchestrator, app_name="gonogo", session_service=session_service)
    
    final_text = ""
    
    # Run the orchestrator agent and trace progress
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)])
    ):
        # Print progress and status changes
        if event.content and event.content.parts:
            text = event.content.parts[0].text
            # Skip printing raw output if it looks like the final response JSON
            if text and not text.strip().startswith("{") and not text.strip().startswith("```json"):
                # Clean up multiple newlines/whitespace for cleaner logging
                clean_text = " ".join(text.split())
                if clean_text:
                    author_color = COLOR_YELLOW
                    if event.author == "conditions_agent":
                        author_color = COLOR_GREEN
                    elif event.author == "advisor_agent":
                        author_color = COLOR_RED
                    
                    colored_author = f"{author_color}{event.author}{COLOR_RESET if use_color else ''}"
                    print(f"  ↳ [{colored_author}] {clean_text}")
                    
        # Capture the final LLM response
        if event.author == "advisor_agent" and event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            
    if not final_text:
        print(f"\n[{COLOR_RED}Error{COLOR_RESET if use_color else ''}] Advisor failed to produce a final response.")
        sys.exit(1)
        
    # Parse final response JSON
    try:
        # Extract JSON code block if present
        json_content = final_text.strip()
        match = re.search(r"```json\s*(.*?)\s*```", final_text, re.DOTALL)
        if match:
            json_content = match.group(1).strip()
            
        data = json.loads(json_content)
    except Exception as e:
        print(
            f"\n[{COLOR_RED}Error{COLOR_RESET if use_color else ''}] Failed to parse Advisor response as JSON.\n"
            f"Details: {e}\n"
            f"Raw Response:\n{final_text}",
            file=sys.stderr
        )
        sys.exit(1)
        
    top_rec = data.get("top_recommendation", "No recommendation generated.")
    region_notes = data.get("region_notes", {})
    
    # Display the final structured output
    border = "=" * 85
    print("\n" + border)
    print("                       GoNoGo CONDITIONS RECOMMENDATION")
    print(border)
    print()
    
    green_ansi = COLOR_GREEN if use_color else ""
    reset_ansi = COLOR_RESET if use_color else ""
    print(f"🏆 {green_ansi}TOP RECOMMENDATION:{reset_ansi}")
    print(f"   {top_rec}")
    print()
    print(border)
    print("                       REGIONAL CONDITIONS NOTES")
    print(border)
    print()
    
    # Load and display regions sorted North-to-South
    regions = load_regions_data()
    for idx, reg in enumerate(regions, start=1):
        r_id = reg["region_id"]
        note = region_notes.get(r_id, "No note generated.")
        
        # Resolve headline peak name
        headline_name = ""
        for peak in reg["peaks"]:
            if peak.get("peak_id") == reg["headline_peak_id"]:
                headline_name = peak["name"]
                break
        if not headline_name and reg["peaks"]:
            headline_name = reg["peaks"][0]["name"]
            
        print(f"{idx:2d}. {reg['name']} (Headline Peak: {headline_name})")
        print(f"    Note: {note}")
        print()
        
    print(border)

def main():
    parser = argparse.ArgumentParser(description="GoNoGo Mountaineering Conditions Board CLI")
    parser.add_argument(
        "--date",
        type=str,
        help="Target start date (YYYY-MM-DD). Defaults to tomorrow."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="Optional target end date (YYYY-MM-DD) for a custom range."
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in output."
    )
    
    args = parser.parse_args()
    
    # Calculate tomorrow as default start date
    today = date.today()
    default_start_str = (today + timedelta(days=1)).isoformat()  # tomorrow
    
    start_str = args.date or default_start_str
    use_color = not args.no_color
    
    # Run pipeline inside async loop
    asyncio.run(run_pipeline(start_str, args.end_date, use_color))

if __name__ == "__main__":
    main()
