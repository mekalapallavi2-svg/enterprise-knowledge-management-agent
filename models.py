from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class SearchConstraints(BaseModel):
    department: Optional[str] = None
    doc_type: Optional[str] = None
    date_range: Optional[DateRange] = None

class AnalyzeRequest(BaseModel):
    query: str
    api_key: str
    audience: Optional[str] = "analyst"
    simulate_hallucination: Optional[bool] = False
    constraints: Optional[SearchConstraints] = None

class ChunkMetadata(BaseModel):
    date: str
    author: str
    department: str
    doc_type: Optional[str] = None

class RetrievedChunk(BaseModel):
    chunk_id: str
    source_document: str
    page_or_section: str
    relevance_score: float
    content: str
    metadata: ChunkMetadata

class TraceStep(BaseModel):
    agent: str
    status: str  # SUCCESS, FAIL, RETRY, SKIP
    timestamp: str
    log: str
    payload: Optional[Dict[str, Any]] = None

class IssueDetail(BaseModel):
    issue_type: str  # HALLUCINATION, PHANTOM_CITATION, CONTRADICTION, SCOPE_VIOLATION, TONE
    location: str
    explanation: str
    suggested_fix: str

class ValidationResult(BaseModel):
    validation_status: str  # PASS, FAIL, PASS_WITH_WARNINGS
    score: int
    issues: List[IssueDetail]
    approved_for_delivery: bool
    validator_note: str

class AnalyzeResponse(BaseModel):
    query: str
    intent: str
    entities: List[str]
    constraints: Dict[str, Any]
    response_text: str
    validation: ValidationResult
    trace: List[TraceStep]
    chunks: List[RetrievedChunk]

class DocumentIndexRequest(BaseModel):
    title: str
    content: str
    metadata: Dict[str, Any]

class DocumentIndexResponse(BaseModel):
    status: str
    chunk_count: int
    message: str
