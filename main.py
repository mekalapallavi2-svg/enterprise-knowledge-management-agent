import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from models import AnalyzeRequest, AnalyzeResponse, DocumentIndexRequest, DocumentIndexResponse
from database import db
from orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

app = FastAPI(
    title="ACME CORP Agent Orchestrator",
    description="ACME Corp Knowledge Management System with Visual Agent Coordination"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing ACME CORP Knowledge Base...")
    docs_dir = "docs"
    
    predefined_meta = {
        "hr_policy.md": {
            "date": "2025-06-15",
            "author": "HR Department",
            "department": "Human Resources",
            "doc_type": "Policy"
        },
        "data_privacy_policy.md": {
            "date": "2025-09-10",
            "author": "CISO Office",
            "department": "Information Security",
            "doc_type": "Policy"
        },
        "employee_handbook.md": {
            "date": "2025-01-10",
            "author": "HR Operations Team",
            "department": "Human Resources",
            "doc_type": "Policy"
        }
    }
    
    if os.path.exists(docs_dir):
        files_indexed = 0
        for filename in os.listdir(docs_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(docs_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    meta = predefined_meta.get(filename, {
                        "date": "2025-01-01",
                        "author": "System",
                        "department": "General",
                        "doc_type": "Policy"
                    })
                    
                    title_match = os.path.splitext(filename)[0].replace("_", " ").title()
                    for line in content.split("\n"):
                        if line.startswith("# "):
                            title_match = line.replace("# ", "").strip()
                            break
                            
                    chunks_added = db.add_document(title_match, content, meta)
                    logger.info(f"Indexed ACME document: {title_match} ({chunks_added} chunks added).")
                    files_indexed += 1
                except Exception as e:
                    logger.error(f"Failed to read/index {filename}: {e}")
        
        logger.info(f"ACME CORP Knowledge base pre-indexing completed. Indexed {files_indexed} documents.")
    else:
        logger.warning("Docs directory 'docs/' not found. Startup pre-indexing skipped.")

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(req: AnalyzeRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not req.api_key.strip():
        raise HTTPException(status_code=400, detail="Groq API Key is required.")

    logger.info(f"Running ACME Corp agent coordination pipeline for: \"{req.query}\"")
    try:
        constraints_dict = None
        if req.constraints:
            constraints_dict = req.constraints.dict(exclude_none=True)
            
        result = await Orchestrator.run(
            query=req.query,
            api_key=req.api_key,
            audience=req.audience,
            simulate_hallucination=req.simulate_hallucination,
            constraints=constraints_dict
        )
        return result
    except Exception as e:
        logger.exception("Pipeline execution failed:")
        raise HTTPException(status_code=500, detail=f"Agent Pipeline Execution Failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    docs_summary = []
    for title, doc_info in db.documents.items():
        doc_chunks = [c for c in db.chunks if c["source_document"] == title]
        docs_summary.append({
            "title": title,
            "metadata": doc_info["metadata"],
            "chunk_count": len(doc_chunks),
            "content": doc_info["content"],
            "content_preview": doc_info["content"][:200] + "..." if len(doc_info["content"]) > 200 else doc_info["content"],
            "chunks": [{"chunk_id": c["chunk_id"], "page_or_section": c["page_or_section"], "content": c["content"]} for c in doc_chunks]
        })
    return docs_summary

@app.post("/index", response_model=DocumentIndexResponse)
async def index_document(req: DocumentIndexRequest):
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required.")
    
    logger.info(f"Indexing new document: {req.title}")
    try:
        chunks_added = db.add_document(req.title, req.content, req.metadata)
        return {
            "status": "success",
            "chunk_count": chunks_added,
            "message": f"Successfully indexed '{req.title}' with {chunks_added} chunks."
        }
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting ACME CORP Agent system server...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
