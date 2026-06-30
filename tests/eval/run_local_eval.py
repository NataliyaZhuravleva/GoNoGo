# © 2026 Nataliya Zhuravleva. All rights reserved.
import glob
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from google.genai import Client


def main():
    # 1. Load env variables
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=dotenv_path)

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No API key found in .env. Please set GOOGLE_API_KEY.")

    # 2. Find the latest traces file
    traces_dir = os.path.join(project_root, "artifacts", "traces")
    trace_files = glob.glob(os.path.join(traces_dir, "traces_*.json"))
    if not trace_files:
        raise FileNotFoundError(
            f"No traces files found in {traces_dir}. Run `agents-cli eval generate` first."
        )
    latest_trace_file = max(trace_files, key=os.path.getmtime)

    print(f"Loading traces from: {os.path.basename(latest_trace_file)}...")
    with open(latest_trace_file, encoding="utf-8") as f:
        trace_data = json.load(f)

    client = Client(api_key=api_key)

    eval_case_results = []
    scores = []

    print("\nEvaluating cases with local LLM Judge...")
    for idx, case in enumerate(trace_data.get("eval_cases", [])):
        case_id = case.get("eval_case_id", f"case_{idx}")
        print(f" -> Grading case: '{case_id}'...")

        # Extract prompt & response
        prompt_text = ""
        prompt_parts = case.get("prompt", {}).get("parts", [])
        if prompt_parts:
            prompt_text = prompt_parts[0].get("text", "")
        else:
            turns = (case.get("agent_data") or {}).get("turns", [])
            if turns:
                prompt_text = str(turns)

        response_text = (
            case.get("responses", [{}])[0]
            .get("response", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        rubric = f"""
        You are an expert Pacific Northwest mountaineering QA evaluator. 
        Your task is to grade the AI agent's response on a scale from 1 to 5 based on whether it provides all the required weather and hazard data necessary for a climber to make a safe decision, and whether its top recommendation follows safety ranking rules.
        
        ### Grading Criteria:
        1 (Poor): Response lacks critical forecast information, fails to follow JSON format, OR violates safety rules by recommending an option with Red hazards when safer zero-Red options are available, OR fails to recommend staying home when all options contain Red hazards.
        3 (Acceptable): Response provides a recommendation and notes, but misses details on one or more key weather parameters, or has minor ranking flaws.
        5 (Excellent): Response is in clean JSON format, successfully evaluates all required weather parameters (winds, freezing level, precipitation type, visibility) across all regions, AND its top recommendation correctly prioritizes zero-Red safety options or recommends staying home if all options are hazardous (Red).
          
        Evaluate if the AI Response provides sufficient details on these parameters so a climber has all the necessary data to make a safe decision, and check if the top recommendation aligns with the safety ranking rules.
        
        User Prompt: {prompt_text}
        AI Response: {response_text}
        
        Return a JSON object matching this structure:
        {{"score": <1-5>, "explanation": "<reason>"}}
        """

        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=rubric,
                config={"response_mime_type": "application/json"},
            )
            grade = json.loads(res.text)
            score = int(grade.get("score", 3))
            explanation = grade.get("explanation", "")
        except Exception as e:
            score = 1
            explanation = f"Failed to call evaluation API: {e}"

        scores.append(score)
        eval_case_results.append(
            {
                "eval_case_index": idx,
                "eval_case_id": case_id,
                "response_candidate_results": [
                    {
                        "response_index": 0,
                        "metric_results": {
                            "local_response_quality": {
                                "metric_name": "local_response_quality",
                                "score": score,
                                "explanation": explanation,
                            }
                        },
                    }
                ],
            }
        )

    # 3. Compute statistics
    mean_score = sum(scores) / len(scores) if scores else 0.0
    pass_rate = sum(1 for s in scores if s >= 3) / len(scores) if scores else 0.0

    results_payload = {
        "eval_case_results": eval_case_results,
        "summary_metrics": [
            {
                "metric_name": "local_response_quality",
                "num_cases_total": len(scores),
                "num_cases_valid": len(scores),
                "num_cases_error": 0,
                "mean_score": mean_score,
                "pass_rate": pass_rate,
            }
        ],
    }

    # 4. Save results
    grade_dir = os.path.join(project_root, "artifacts", "grade_results")
    os.makedirs(grade_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_json_path = os.path.join(grade_dir, f"results_{timestamp}.json")

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print("\n" + "=" * 50)
    print("                 Evaluation Summary                  ")
    print("=" * 50)
    print(f"Total Cases:     {len(scores)}")
    print(f"Mean Score:      {mean_score:.2f}")
    print(f"Pass Rate:       {pass_rate * 100:.1f}%")
    print("=" * 50)
    for res in eval_case_results:
        c_id = res["eval_case_id"]
        metric = res["response_candidate_results"][0]["metric_results"][
            "local_response_quality"
        ]
        print(f"Case: {c_id:<15} Score: {metric['score']}/5")
        print(f"Explanation: {metric['explanation']}\n")
    print(f"Saved full results to: artifacts/grade_results/results_{timestamp}.json")


if __name__ == "__main__":
    main()
