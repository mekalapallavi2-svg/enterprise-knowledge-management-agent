import asyncio
import os
import sys
import json
from unittest.mock import patch, AsyncMock
from database import db
from orchestrator import Orchestrator

def init_db():
    docs_dir = "docs"
    predefined_meta = {
        "hr_policy.md": {"date": "2025-06-15", "author": "HR Department", "department": "Human Resources", "doc_type": "Policy"},
        "data_privacy_policy.md": {"date": "2025-09-10", "author": "CISO Office", "department": "Information Security", "doc_type": "Policy"},
        "employee_handbook.md": {"date": "2025-01-10", "author": "HR Operations Team", "department": "Human Resources", "doc_type": "Policy"}
    }
    
    if os.path.exists(docs_dir):
        for filename in os.listdir(docs_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(docs_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                meta = predefined_meta.get(filename, {"date": "2025-01-01", "author": "System", "department": "General", "doc_type": "Policy"})
                title = filename.replace("_", " ").replace(".md", "").title()
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line.replace("# ", "").strip()
                        break
                db.add_document(title, content, meta)

MOCK_ORCH_RESPONSE = {
    "intent": "Q&A",
    "entities": ["Leave Policy"],
    "constraints": { "date_range": None, "department": "Human Resources", "doc_type": "Policy" }
}

MOCK_VARIANTS = {
    "variants": [
        "employee annual leave rollover limits",
        "vacation rollover guidelines HR policy",
        "paid vacation roll over March expiration date"
    ]
}

MOCK_SYNTHESIS = (
    "**Answer:** In compliance with the Leave Policy Guidelines, standard full-time employees are entitled to roll over up to 5 unused vacation days into the next calendar year. These rolled-over days must be utilized before they expire on March 31.\n\n"
    "**Supporting Evidence:**\n"
    "- [Source: Leave Policy Guidelines, Section: Section 1: Annual Leave Allowance] -> Up to 5 unused vacation days can be rolled over to the next calendar year, and these rolled-over days will expire on March 31 of that next year."
)

MOCK_VALIDATION = {
    "validation_status": "PASS",
    "score": 100,
    "issues": [],
    "approved_for_delivery": True,
    "validator_note": "Factual checking completed. Response is fully grounded in the retrieved Leave Policy document."
}

async def mock_call_groq(system_prompt: str, user_prompt: str, api_key: str, json_mode: bool = False) -> str:
    if "Orchestrator" in system_prompt:
        return json.dumps(MOCK_ORCH_RESPONSE)
    elif "Retrieval Agent" in system_prompt:
        return json.dumps(MOCK_VARIANTS)
    elif "Validation Agent" in system_prompt:
        return json.dumps(MOCK_VALIDATION)
    elif "Synthesis Agent" in system_prompt:
        return MOCK_SYNTHESIS
    return "Mock Response"

async def test_pipeline_dry_run():
    print("==================================================")
    print("Agent Pipeline Integration Trace Verification")
    print("==================================================")
    
    init_db()
    print("Initialized database for search verification.")
    
    query = "What is the rollover policy on annual leave?"
    api_key = os.environ.get("GROQ_API_KEY", "mock_key")
    
    print(f"\nRunning query: \"{query}\"")
    
    if api_key == "mock_key":
        print("[Notice] No GROQ_API_KEY environment variable detected. Running in MOCK LLM Dry-Run mode.")
        with patch("orchestrator.call_groq_api", new=mock_call_groq), \
             patch("agents.call_groq_api", new=mock_call_groq):
            result = await Orchestrator.run(query=query, api_key=api_key)
    else:
        print("[Notice] GROQ_API_KEY detected! Testing live connection to Groq API...")
        result = await Orchestrator.run(query=query, api_key=api_key)
        
    print("\n----------------- PIPELINE TRACE LOGS -----------------")
    for step in result["trace"]:
        status_color = "\033[92m" if step["status"] == "SUCCESS" else "\033[91m"
        print(f"[{step['timestamp']}] {step['agent']:<22} | {status_color}{step['status']:<7}\033[0m | {step['log']}")
        
    print("\n------------------- CHUNKS MATCHED --------------------")
    for idx, c in enumerate(result["chunks"]):
        print(f"[{idx+1}] Score: {c['relevance_score']} | Source: {c['source_document']} | Section: {c['page_or_section']}")
        
    print("\n------------------ GROUNDED ANSWER --------------------")
    print(result["response_text"])
    
    print("\n----------------- VALIDATION SUMMARY ------------------")
    val = result["validation"]
    print(f"Status: {val['validation_status']} | Score: {val['score']}/100")
    print(f"Validator Review: {val['validator_note']}")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_pipeline_dry_run())
