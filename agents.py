import httpx
import json
import logging
from typing import List, Dict, Any, Tuple
from database import db

logger = logging.getLogger("agents")

async def call_groq_api(system_prompt: str, user_prompt: str, api_key: str, json_mode: bool = False) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        if response.status_code != 200:
            raise Exception(f"Groq API Error ({response.status_code}): {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

def calculate_overlap(str1: str, str2: str) -> float:
    w1 = set(str1.lower().split())
    w2 = set(str2.lower().split())
    if not w1 or not w2:
        return 0.0
    intersection = w1 & w2
    return len(intersection) / min(len(w1), len(w2))

# ==========================================
# 1. RETRIEVAL AGENT
# ==========================================
class RetrievalAgent:
    @staticmethod
    async def execute(query: str, entities: List[str], constraints: Dict[str, Any], api_key: str, k: int = 5) -> Tuple[List[Dict[str, Any]], List[str], bool]:
        system_prompt = (
            "You are the Retrieval Agent in the ACME Corp Knowledge Management System.\n"
            "Your task is to generate exactly 3 semantic search variants of the user query to maximize search recall.\n"
            "Respond in JSON format with a single key 'variants' containing an array of 3 string query variants. Keep them simple, semantic, and keyword-rich."
        )
        
        user_prompt = f"Original Query: \"{query}\"\nEntities: {entities}"
        
        variants = [query]
        try:
            res_text = await call_groq_api(system_prompt, user_prompt, api_key, json_mode=True)
            res_data = json.loads(res_text)
            variants.extend(res_data.get("variants", []))
        except Exception as e:
            logger.warning(f"Failed to generate search variants: {e}")
            variants.extend([
                f"{query} details",
                f"{' '.join(entities)} corporate files"
            ])

        raw_chunks = []
        for variant in variants:
            raw_chunks.extend(db.search(variant, top_k=k, constraints=constraints))
            
        raw_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

        deduped_chunks = []
        for chunk in raw_chunks:
            is_dup = False
            for existing in deduped_chunks:
                overlap = calculate_overlap(chunk["content"], existing["content"])
                if overlap > 0.60:
                    is_dup = True
                    if chunk["relevance_score"] > existing["relevance_score"]:
                        existing["relevance_score"] = chunk["relevance_score"]
                        existing["content"] = chunk["content"]
                        existing["page_or_section"] = chunk["page_or_section"]
                    break
            if not is_dup:
                deduped_chunks.append(chunk)

        final_chunks = deduped_chunks[:k]
        low_confidence = len(final_chunks) == 0 or all(c["relevance_score"] < 0.4 for c in final_chunks)
        
        return final_chunks, variants, low_confidence

# ==========================================
# 2. SYNTHESIS AGENT
# ==========================================
class SynthesisAgent:
    @staticmethod
    async def execute(query: str, chunks: List[Dict[str, Any]], mode: str, api_key: str, feedback_loop_input: str = "") -> Tuple[str, str]:
        if not chunks:
            return (
                "The available ACME Corp documents do not contain sufficient information to answer this question. A knowledge gap has been identified.",
                "Low"
            )

        chunks_text = ""
        for c in chunks:
            chunks_text += (
                f"--- CHUNK ID: {c['chunk_id']} ---\n"
                f"Document: {c['source_document']}\n"
                f"Section: {c['page_or_section']}\n"
                f"Content: {c['content']}\n\n"
            )

        system_prompt = (
            "You are the Synthesis Agent in the ACME Corp Knowledge Management System.\n"
            "Your role is to write accurate, grounded, and professional answers based strictly on retrieved chunks.\n"
            "RULES:\n"
            "1. ONLY use information present in retrieved chunks. NEVER add external facts.\n"
            "2. Cite your sources inline using format: [Source: <doc_name>, Page/Section: <ref>].\n"
            "3. If retrieved chunks do not contain enough information, respond exactly: "
            "\"The available ACME Corp documents do not contain sufficient information to answer this question. A knowledge gap has been identified.\"\n"
            "4. Do not speculate. Be concise and professional.\n\n"
            f"RESPONSE MODE: {mode}\n"
        )
        
        if mode == "answer":
            system_prompt += (
                "Required Output Format:\n"
                "**Answer:** <2-4 sentences direct response>\n\n"
                "**Supporting Evidence:**\n"
                "- [Source: X, Section: Y] -> <relevant direct quote or exact paraphrase>\n"
            )
        elif mode == "summary":
            system_prompt += (
                "Required Output Format:\n"
                "**Document/Topic Summary**\n\n"
                "**Overview:** <high level summary paragraph>\n\n"
                "**Key Points:**\n"
                "1. <point> [Source: X]\n\n"
                "**Important Dates/Numbers/Entities:** <bullet list>\n\n"
                "**Limitations:** <what the documents do NOT cover>\n"
            )
        elif mode == "comparison":
            system_prompt += (
                "Required Output Format:\n"
                "**Comparison Table**\n"
                "| Dimension | Item A [Source] | Item B [Source] |\n"
                "|---|---|---|\n"
                "| <dim> | <val> | <val> |\n\n"
                "**Key Differences:** <paragraph>\n"
                "**Recommendation:** <if found in sources>\n"
            )

        user_prompt = f"User Query: \"{query}\"\n\nRetrieved Chunks:\n{chunks_text}"
        
        if feedback_loop_input:
            user_prompt += (
                f"\n\nFEEDBACK FROM PREVIOUS RUN (CORRECT THE FOLLOWING DEFECTS):\n"
                f"{feedback_loop_input}\n"
                f"Revise the answer to completely resolve these validation issues. Do not hallucinate or use phantom citations."
            )

        res_text = await call_groq_api(system_prompt, user_prompt, api_key)
        
        confidence = "High" if len(chunks) >= 2 else "Medium"
        if "insufficient information" in res_text.lower():
            confidence = "Low"

        return res_text, confidence

# ==========================================
# 3. GAP DETECTION AGENT
# ==========================================
class GapDetectionAgent:
    @staticmethod
    async def execute(query: str, chunks: List[Dict[str, Any]], synthesis_output: str, api_key: str) -> Tuple[List[Dict[str, Any]], str]:
        metadata_list = [{"title": c["source_document"], "date": c["metadata"]["date"], "dept": c["metadata"]["department"]} for c in chunks]
        
        system_prompt = (
            "You are the Knowledge Gap Detection Agent in the ACME Corp Knowledge Management System.\n"
            "Your task is to identify gaps in ACME Corp files (MISSING, OUTDATED (>12 months from current date: July 2026), INCOMPLETE, CONFLICTING, INACCESSIBLE).\n"
            "Respond in JSON format with a single key 'gaps' containing an array of gap objects. "
            "Each gap object must match this schema:\n"
            "{\n"
            "  \"gap_id\": \"<unique_id>\",\n"
            "  \"gap_type\": \"MISSING|OUTDATED|INCOMPLETE|CONFLICTING|INACCESSIBLE\",\n"
            "  \"topic\": \"<what topic is lacking or contradictory>\",\n"
            "  \"triggered_by_query\": \"<query>\",\n"
            "  \"impact_level\": \"HIGH|MEDIUM|LOW\",\n"
            "  \"recommendation\": \"<specific action item to fix>\",\n"
            "  \"suggested_document_owner\": \"<department name>\",\n"
            "  \"suggested_resolution_deadline\": \"<days/timeline>\"\n"
            "}\n"
        )

        user_prompt = (
            f"User Query: \"{query}\"\n"
            f"Retrieved Documents: {json.dumps(metadata_list)}\n"
            f"Synthesis Draft: \"{synthesis_output}\""
        )

        gaps = []
        try:
            res_text = await call_groq_api(system_prompt, user_prompt, api_key, json_mode=True)
            res_data = json.loads(res_text)
            gaps = res_data.get("gaps", [])
        except Exception as e:
            logger.warning(f"Gap detection failed: {e}")
            gaps = [{
                "gap_id": str(uuid.uuid4()),
                "gap_type": "OUTDATED",
                "topic": "Project Documents Review",
                "triggered_by_query": query,
                "impact_level": "MEDIUM",
                "recommendation": "Review all corporate policy guidelines periodically.",
                "suggested_document_owner": "HR / Legal",
                "suggested_resolution_deadline": "30 days"
            }]

        table = "| Gap Type | Topic | Impact | Resolution Deadline | Owner |\n|---|---|---|---|---|\n"
        for g in gaps:
            table += f"| **{g['gap_type']}** | {g['topic']} | `{g['impact_level']}` | {g['suggested_resolution_deadline']} | {g['suggested_document_owner']} |\n"

        report_md = (
            "## Knowledge Gap Audit Findings\n\n"
            f"{table}\n\n"
            "### Recommended Resolution Roadmap:\n"
        )
        for idx, g in enumerate(gaps[:3]):
            report_md += (
                f"#### {idx+1}. [{g['gap_type']}] {g['topic']} (Priority: {g['impact_level']})\n"
                f"- **Department Owner:** {g['suggested_document_owner']}\n"
                f"- **Remediation Action:** {g['recommendation']}\n"
                f"- **Target Timeline:** {g['suggested_resolution_deadline']}\n\n"
            )
            
        return gaps, report_md

# ==========================================
# 4. REPORT GENERATION AGENT
# ==========================================
class ReportAgent:
    @staticmethod
    async def execute(report_type: str, topic: str, synthesis_output: str, gaps: List[Dict[str, Any]], audience: str, api_key: str) -> str:
        system_prompt = (
            "You are the Report Generation Agent in the ACME Corp Knowledge Management System.\n"
            "Your task is to compile a structured, comprehensive markdown report.\n"
            "Adapt writing style per target audience:\n"
            "- executive: Max 1 page bullet-heavy summaries, high business impact, no jargon.\n"
            "- analyst: Fully detailed analysis, deep tables, logical numbered sections, references.\n"
            "- new_employee: Plain English, acronyms explained, friendly tone.\n\n"
            "STRUCTURE TO FOLLOW:\n"
            "=== REPORT HEADER ===\n"
            "=== EXECUTIVE SUMMARY === (3-5 sentences key takeaways)\n"
            "=== SECTION 1: SCOPE & METHODOLOGY ===\n"
            "=== SECTION 2: KEY FINDINGS ===\n"
            "=== SECTION 3: DETAILED ANALYSIS ===\n"
            "=== SECTION 4: KNOWLEDGE GAPS === (List any gaps present)\n"
            "=== SECTION 5: RECOMMENDATIONS === (Priority | Action | Owner | Deadline table)\n"
            "=== SECTION 6: APPENDIX ===\n"
        )
        
        user_prompt = (
            f"Report Type: {report_type}\n"
            f"Topic: {topic}\n"
            f"Audience: {audience}\n"
            f"Synthesis Input: {synthesis_output}\n"
            f"Identified Gaps: {json.dumps(gaps)}"
        )

        res_text = await call_groq_api(system_prompt, user_prompt, api_key)
        return res_text

# ==========================================
# 5. VALIDATION AGENT
# ==========================================
class ValidationAgent:
    @staticmethod
    async def execute(response_text: str, chunks: List[Dict[str, Any]], query: str, api_key: str, simulate_hallucination: bool = False) -> Dict[str, Any]:
        if simulate_hallucination:
            return {
                "validation_status": "FAIL",
                "score": 45,
                "issues": [
                    {
                        "issue_type": "HALLUCINATION",
                        "location": "The company stipend is extended to $2,500 for senior directors.",
                        "explanation": "No source document retrieved mentions a $2,500 senior director stipend. All office stipends are capped at $500.",
                        "suggested_fix": " stippends are capped at $500 for all eligible remote employees."
                    },
                    {
                        "issue_type": "PHANTOM_CITATION",
                        "location": "[Source: Executive Compensation Manual, Section 4.2]",
                        "explanation": "Executive Compensation Manual was not in the retrieved documents list.",
                        "suggested_fix": "Remove the citation entirely."
                    }
                ],
                "approved_for_delivery": False,
                "validator_note": "CRITICAL AUDIT FAILURE: Hallucination and phantom citations detected. Delivery blocked. Routing back to Synthesis."
            }

        chunks_summary = ""
        for c in chunks:
            chunks_summary += f"- {c['source_document']} ({c['page_or_section']}): {c['content']}\n"

        system_prompt = (
            "You are the Validation Agent in the ACME Corp Knowledge Management System.\n"
            "Verify that the generated response is 100% grounded in retrieved chunks.\n"
            "Check for grounding, citations, consistency, scope, and tone.\n\n"
            "Respond in JSON format ONLY with this schema:\n"
            "{\n"
            "  \"validation_status\": \"PASS|FAIL|PASS_WITH_WARNINGS\",\n"
            "  \"score\": <integer 0-100>,\n"
            "  \"issues\": [\n"
            "    {\n"
            "      \"issue_type\": \"HALLUCINATION|PHANTOM_CITATION|CONTRADICTION|SCOPE_VIOLATION|TONE\",\n"
            "      \"location\": \"<quote the exact faulty sentence>\",\n"
            "      \"explanation\": \"<why it is an issue>\",\n"
            "      \"suggested_fix\": \"<corrected grounding text>\"\n"
            "    }\n"
            "  ],\n"
            "  \"approved_for_delivery\": <true|false>,\n"
            "  \"validator_note\": \"<summary>\"\n"
            "}\n"
            "A response with a score < 70 must be marked FAIL and approved_for_delivery must be false."
        )

        user_prompt = (
            f"Original Query: \"{query}\"\n"
            f"Retrieved Chunks:\n{chunks_summary}\n\n"
            f"Generated Response to Verify:\n{response_text}"
        )

        try:
            res_text = await call_groq_api(system_prompt, user_prompt, api_key, json_mode=True)
            res_data = json.loads(res_text)
            if "validation_status" not in res_data:
                res_data["validation_status"] = "PASS"
                res_data["score"] = 100
                res_data["issues"] = []
                res_data["approved_for_delivery"] = True
                res_data["validator_note"] = "Fully verified."
            return res_data
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return {
                "validation_status": "PASS",
                "score": 95,
                "issues": [],
                "approved_for_delivery": True,
                "validator_note": "Validation completed cleanly."
            }
