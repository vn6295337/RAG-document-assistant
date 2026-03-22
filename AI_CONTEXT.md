# AI Context: RAG Document Assistant (Production Prototype)

This document serves as the single source of truth for the RAG Document Assistant. It is designed to provide immediate, high-density context for any AI assistant (e.g., Claude Code, Gemini) taking over the project.

## 1. Core Mission & Philosophy
**Privacy-First "Zero-Storage" RAG.**
The system enables natural language search over private documents without ever storing the raw text on the server or in a database.
- **No Disk Persistence**: Files are processed in RAM (`BytesIO`).
- **No Database Text**: Pinecone stores only embeddings and character-position metadata.
- **Re-fetch at Query Time**: Original text is retrieved fresh from the user's Dropbox for every query.
- **User Ownership**: Disconnecting Dropbox immediately revokes all access to document content.

## 2. Technical Stack
- **Backend**: FastAPI (Python 3.8+)
- **Frontend**: React 18 + Vite + Tailwind CSS v4
- **Parsing**: **Docling** (Layout-aware, structure-preserving)
- **Vector DB**: **Pinecone Serverless** (384-dim, Cosine)
- **Embedding**: `sentence-transformers/all-MiniLM-L6-v2` (via HuggingFace API in production)
- **LLM Gateway**: **LiteLLM** (Unified access to Gemini 2.5 Flash, Groq, OpenRouter)
- **Observability**: **LangFuse Cloud** (Tracing & Latency monitoring)
- **Security**: **Microsoft Presidio** (PII Scrubbing)

## 3. Hardware Strategy: "Hybrid-Cloud"
Optimized for lightweight hardware (Intel Celeron N3350, 19GB Linux Container).
- **Offload Compute**: All heavy processing (Embeddings, LLMs, Tracing) is sent to Cloud APIs (HuggingFace, Groq, LangFuse) to prevent CPU/RAM saturation.
- **Local Logic**: The FastAPI orchestrator and LiteLLM gateway run locally to manage the pipeline flow.

## 4. Architectural Data Flow
### Indexing (Single Download)
1. Browser calls `/parse-docling` (RAM-only parsing on server).
2. Server returns structured elements + full text.
3. Browser performs **Client-Side Chunking** to preserve privacy.
4. Browser sends chunks to `/api/embed-chunks` (Server generates embeddings → Pinecone → Discards text).

### Query (Zero-Storage)
1. User query → `/query-secure`.
2. Query Rewriting (LiteLLM) → Vector Search (Pinecone).
3. **Re-fetch from Dropbox**: Download file → Extract text using metadata positions.
4. Reranking (Cross-Encoder) → Context Shaping (Token budget).
5. Generation (LiteLLM) → Return Answer + Citations.

## 5. Directory Structure & Key Files
- `src/api/routes.py`: FastAPI endpoints. (Note: `/query-secure` is the production path).
- `src/orchestrator.py`: Central RAG pipeline logic.
- `src/ingestion/docling_loader.py`: RAM-only parsing logic.
- `src/llm_providers.py`: Unified LLM access (LiteLLM integration target).
- `frontend/src/api/chunker.js`: Client-side privacy logic.

## 6. Implementation Roadmap (Next Steps)
1. **Unify Orchestration**: Move the logic from `routes.py:query_secure` into `orchestrator.py`.
2. **Streaming Support**: Refactor the query pipeline to support Server-Sent Events (SSE) for real-time answer generation.
3. **Observability**: Integrate `Langfuse` decorators into `orchestrator.py`.
4. **Cleanup**: Remove legacy "local storage" endpoints (`/ingest`, `/query`) to strictly enforce the zero-storage policy.

## 7. Obsolete Documentation (Safe to Ignore)
- `Architecture.txt`: Replaced by this document and `docs/architecture.md`.
- `poc_2_prototype.md`: Fully merged into this roadmap.
- `BUSINESS_README.md`: Supplemental, not for technical reference.
