# ACME Corp — Enterprise Knowledge Orchestrator

A multi-agent Retrieval-Augmented Generation (RAG) system that answers questions over enterprise documents, generates summaries, detects knowledge gaps, and compiles structured reports — built as a live, in-browser agentic pipeline with full execution tracing.

> Internship Project — Enterprise Knowledge Management Agent
> Built with [Google Antigravity](https://antigravity.google/) · Powered by [Groq](https://groq.com/)

---

## Overview

Enterprises accumulate policy documents, handbooks, and compliance material across departments, but employees struggle to find accurate, grounded answers quickly, and organizations rarely know what's *missing* from their own knowledge base until it's too late.

This project implements a **6-agent orchestration pipeline** that:

- Classifies user intent (Q&A, Summary, Gap Analysis, Report Generation, Hybrid)
- Retrieves relevant document chunks from an indexed vector store
- Synthesizes grounded, cited answers — strictly from retrieved context, never from model memory
- Detects knowledge gaps (missing, outdated, incomplete, or conflicting information)
- Generates structured, audience-aware reports (executive / manager / analyst / new employee)
- Validates every response for hallucinations, phantom citations, and scope violations before delivery

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│ NLU Classify │  → intent, entities, constraints
└──────┬──────┘
       ▼
┌─────────────┐
│  Retrieval   │  → query reformulation, vector search, top-K chunks
└──────┬──────┘
       ▼
┌─────────────┐
│  Synthesis   │  → grounded, cited response generation (Groq LLM)
└──────┬──────┘
       ▼
┌─────────────┐      ┌───────────────┐      ┌──────────────┐
│  Validation  │ ───▶ │  Gap Detector │ ───▶ │ Report Agent │
└─────────────┘      └───────────────┘      └──────────────┘
```

Each stage in the pipeline is visualized live in the UI, with a **sub-agent execution trace** showing every retrieval, synthesis call, and validation check as it happens — including a self-correcting loop: if validation fails (e.g. a phantom citation), the query is automatically routed back to the Synthesis Agent for revision.

## Features

- **Vector Database Store** — browse and index enterprise documents (policies, handbooks, compliance docs) with department/type tagging
- **Query Analysis** — intent classification, key entity extraction, and constraint/filter detection before retrieval
- **Grounded Responses** — every claim is traceable to a retrieved source chunk, with an explicit confidence score
- **Knowledge Gap Detection** — flags MISSING, OUTDATED, INCOMPLETE, and CONFLICTING information, each scored by business impact
- **Automated Report Generation** — compiles findings into structured reports (Knowledge Summary, Gap Analysis, Compliance Audit, Onboarding Brief) tailored to the target audience
- **Validation Layer** — a dedicated agent checks grounding, citation accuracy, internal consistency, and tone before anything reaches the user
- **Live Execution Trace** — a real-time log of every sub-agent call, timing, and success/failure state

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML / CSS / JavaScript |
| LLM Inference | [Groq API](https://console.groq.com/docs/models) |
| Vector Store | Local/in-browser vector index (document embeddings + similarity search) |
| Orchestration | Custom multi-agent router (Orchestrator → Retrieval → Synthesis → Gap Detection → Report → Validation) |

## Getting Started

### Prerequisites
- A [Groq API key](https://console.groq.com/keys)
- Python 3 (for local dev server) or any static file server

### Setup

```bash
git clone https://github.com/<your-username>/acme-knowledge-orchestrator.git
cd acme-knowledge-orchestrator
```

Add your Groq API key to the config (see `config/` or the in-app settings panel, depending on your build).

> **Note:** Groq periodically deprecates older models. If you see a `model_decommissioned` error, check [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations) and update the model ID in your config — as of mid-2026, `openai/gpt-oss-20b` and `openai/gpt-oss-120b` are the recommended general-purpose models.

### Run locally

```bash
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## Usage

1. **Index documents** — add enterprise documents (policies, handbooks, etc.) via the "Index Document" tab.
2. **Ask a question** — type a query like *"What is the company leave policy for employees?"*
3. **Watch the pipeline** — the agent network shows each stage activating in real time.
4. **Review the response** — check the grounded answer, confidence score, cited sources, and any flagged knowledge gaps.
5. **Generate a report** — for compliance/audit-style queries, the Report Agent compiles a structured document.

## Project Structure

```
acme-knowledge-orchestrator/
├── index.html          # Dashboard layout
├── styles.css           # UI styling
├── knowledgeBase.js      # Document store + retrieval logic
├── agents.js             # Agent orchestration logic (routing, synthesis, validation, etc.)
├── app.js                 # Frontend controller (pipeline execution, UI updates, tracing)
└── README.md
```

## Roadmap / Future Improvements

- [ ] Persist indexed documents to a real vector database (Chroma / Pinecone / FAISS)
- [ ] Add authentication and per-department access control
- [ ] Support PDF/DOCX ingestion with automatic chunking
- [ ] Add a scheduled knowledge-audit trigger for periodic gap detection
- [ ] Multi-turn conversation memory for follow-up questions

## Acknowledgments

Built as part of an internship project on Enterprise Knowledge Management using Retrieval-Augmented Generation (RAG) and multi-agent orchestration.

## License

MIT
