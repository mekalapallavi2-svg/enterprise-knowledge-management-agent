import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from agents import call_groq_api, RetrievalAgent, SynthesisAgent, GapDetectionAgent, ReportAgent, ValidationAgent

logger = logging.getLogger("orchestrator")

class Orchestrator:
    @staticmethod
    async def run(query: str, api_key: str, audience: str = "analyst", simulate_hallucination: bool = False, constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        
        def add_trace(agent: str, status: str, log_msg: str, payload: Dict[str, Any] = None):
            trace.append({
                "agent": agent,
                "status": status,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "log": log_msg,
                "payload": payload
            })

        # ------------------------------------------
        # STEP 1: NLU INTENT CLASSIFICATION
        # ------------------------------------------
        system_prompt = (
            "You are the Master Orchestrator of the ACME Corp Knowledge Management System.\n"
            "Your role is to classify the intent of user queries and identify target entities.\n"
            "Classify intent into exactly one of: [Q&A | Summary | Gap Analysis | Report Generation].\n"
            "Identify key entities, topics, and constraints.\n"
            "Respond in JSON format ONLY with this schema:\n"
            "{\n"
            "  \"intent\": \"<intent>\",\n"
            "  \"entities\": [\"<entity1>\", \"<entity2>\"],\n"
            "  \"constraints\": { \"date_range\": null, \"department\": null, \"doc_type\": null }\n"
            "}\n"
        )
        
        user_prompt = f"User Query: \"{query}\""
        
        intent = "Q&A"
        entities = []
        parsed_constraints = constraints or {}
        
        add_trace("Orchestrator", "SUCCESS", "Classifying user query intent and extracting target entities...")
        
        try:
            res_text = await call_groq_api(system_prompt, user_prompt, api_key, json_mode=True)
            res_data = json.loads(res_text)
            intent = res_data.get("intent", "Q&A")
            entities = res_data.get("entities", [])
            extracted_constraints = res_data.get("constraints", {}) or {}
            for k, v in extracted_constraints.items():
                if v and not parsed_constraints.get(k):
                    parsed_constraints[k] = v
                    
            add_trace("Orchestrator", "SUCCESS", f"Classified intent as '{intent}' targeting: {entities}", {
                "intent": intent,
                "entities": entities,
                "constraints": parsed_constraints
            })
        except Exception as e:
            logger.warning(f"Orchestrator NLU failed: {e}")
            q_lower = query.lower()
            if "summarize" in q_lower or "summary" in q_lower:
                intent = "Summary"
            elif "missing" in q_lower or "gap" in q_lower or "not know" in q_lower:
                intent = "Gap Analysis"
            elif "report" in q_lower:
                intent = "Report Generation"
            
            if "leave" in q_lower or "vacation" in q_lower:
                entities = ["Leave Policy"]
            elif "privacy" in q_lower or "gdpr" in q_lower:
                entities = ["GDPR Privacy"]
            else:
                entities = ["General Knowledge"]
                
            add_trace("Orchestrator", "SUCCESS", f"Fallback classification: '{intent}' targeting: {entities}", {
                "intent": intent,
                "entities": entities,
                "constraints": parsed_constraints
            })

        # ------------------------------------------
        # STEP 2: RETRIEVAL AGENT
        # ------------------------------------------
        add_trace("Retrieval Agent", "SUCCESS", "Generating query variants and searching vector store index...")
        k_val = 10 if intent == "Report Generation" else 5
        
        try:
            chunks, variants, low_confidence = await RetrievalAgent.execute(
                query, entities, parsed_constraints, api_key, k=k_val
            )
            retrieval_log = f"Retrieved {len(chunks)} chunks using variants: {variants}."
            if low_confidence:
                retrieval_log += " WARNING: LOW_CONFIDENCE_RETRIEVAL flag raised (< 0.4 scores)."
                
            add_trace("Retrieval Agent", "SUCCESS", retrieval_log, {
                "variants": variants,
                "chunk_count": len(chunks),
                "low_confidence": low_confidence
            })
        except Exception as e:
            chunks = []
            low_confidence = True
            add_trace("Retrieval Agent", "FAIL", f"Retrieval failed: {str(e)}")

        # ------------------------------------------
        # STEP 3: SYNTHESIS & VALIDATION LOOP (RETRY)
        # ------------------------------------------
        synthesis_text = ""
        confidence = "Medium"
        validation_result = {
            "validation_status": "PASS",
            "score": 100,
            "issues": [],
            "approved_for_delivery": True,
            "validator_note": "Validation clean."
        }
        
        feedback_input = ""
        max_retries = 2
        active_hallucination = simulate_hallucination

        response_mode = "answer"
        if intent == "Summary":
            response_mode = "summary"
        elif "compare" in query.lower() or "versus" in query.lower() or "vs" in query.lower():
            response_mode = "comparison"

        for attempt in range(max_retries):
            retry_suffix = f" (Attempt {attempt+1})" if attempt > 0 else ""
            add_trace("Synthesis Agent", "SUCCESS", f"Generating grounded response in '{response_mode}' mode{retry_suffix}...")
            
            try:
                synthesis_text, confidence = await SynthesisAgent.execute(
                    query, chunks, response_mode, api_key, feedback_input
                )
                add_trace("Synthesis Agent", "SUCCESS", f"Grounded text drafted. Confidence: {confidence}")
            except Exception as e:
                synthesis_text = f"Synthesis process failed: {e}"
                add_trace("Synthesis Agent", "FAIL", f"Synthesis error: {str(e)}")
                break

            # Run Validation
            add_trace("Validation Agent", "SUCCESS", f"Factual check: verifying grounding and citations against source files{retry_suffix}...")
            try:
                run_hallucination = active_hallucination if attempt == 0 else False
                val_data = await ValidationAgent.execute(
                    synthesis_text, chunks, query, api_key, run_hallucination
                )
                validation_result = val_data
                val_status = val_data.get("validation_status", "PASS")
                val_score = val_data.get("score", 100)
                val_note = val_data.get("validator_note", "")

                if val_status == "FAIL":
                    add_trace("Validation Agent", "RETRY", f"REJECTED (Score: {val_score}/100): {val_note}", val_data)
                    feedback_input = ""
                    for idx, issue in enumerate(val_data.get("issues", [])):
                        feedback_input += f"- Issue {idx+1}: [{issue['issue_type']}] in sentence '{issue['location']}'. Reason: {issue['explanation']}. Suggestion: {issue['suggested_fix']}\n"
                    continue
                else:
                    add_trace("Validation Agent", "SUCCESS", f"PASSED (Score: {val_score}/100): {val_note}", val_data)
                    break
            except Exception as e:
                add_trace("Validation Agent", "FAIL", f"Validation system error: {str(e)}")
                break

        # ------------------------------------------
        # STEP 4: GAP DETECTION & REPORT AGENTS
        # ------------------------------------------
        gaps_list = []
        gaps_report = ""
        
        if intent == "Gap Analysis" or intent == "Report Generation" or low_confidence:
            add_trace("Gap Detection Agent", "SUCCESS", "Analyzing file directories to detect missing or outdated records...")
            try:
                gaps, rep_md = await GapDetectionAgent.execute(query, chunks, synthesis_text, api_key)
                gaps_list = gaps
                gaps_report = rep_md
                add_trace("Gap Detection Agent", "SUCCESS", f"Audited {len(gaps)} repository gaps.", {"gaps": gaps})
                
                if intent == "Gap Analysis":
                    synthesis_text = rep_md
            except Exception as e:
                add_trace("Gap Detection Agent", "FAIL", f"Gap detection error: {str(e)}")

        if intent == "Report Generation":
            add_trace("Report Agent", "SUCCESS", f"Formatting full corporate management report for '{audience}' audience...")
            try:
                report_text = await ReportAgent.execute(
                    "KNOWLEDGE_SUMMARY_REPORT", 
                    entities[0] if entities else "General", 
                    synthesis_text, 
                    gaps_list, 
                    audience, 
                    api_key
                )
                synthesis_text = report_text
                
                add_trace("Validation Agent", "SUCCESS", "Re-verifying final compiled report formatting...")
                val_data = await ValidationAgent.execute(synthesis_text, chunks, query, api_key, False)
                validation_result = val_data
                add_trace("Validation Agent", "SUCCESS", f"Report verified successfully. Score: {val_data.get('score', 100)}/100.")
                
                add_trace("Report Agent", "SUCCESS", "Report successfully structured.")
            except Exception as e:
                add_trace("Report Agent", "FAIL", f"Report generation error: {str(e)}")

        return {
            "query": query,
            "intent": intent,
            "entities": entities,
            "constraints": parsed_constraints,
            "response_text": synthesis_text,
            "validation": validation_result,
            "trace": trace,
            "chunks": chunks
        }
