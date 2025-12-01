# poc-rag

## Elevator pitch (3 lines)
Retrieval-Augmented Generation (RAG) prototype that answers policy/process queries from uploaded documents with source citations and traceable evidence.  
Proves end-to-end ingestion → vector index → retrieval → LLM synthesis with transparent citations.  
Designed for rapid deployment on Cloud Run for low-cost, demo-ready operations.

## What this proves (3 bullets)
- Ingestion, chunking, and embedding pipeline integrated with Pinecone/Neon.  
- Reliable retrieval-to-LLM orchestration producing cited answers suitable for CXO demos.  
- Production-capable Streamlit UI deployed on Cloud Run using Buildpacks.

## Quick start
1. Create a Python 3.10+ virtual environment and install deps from `requirements.txt`.  
2. Populate `.env` with `PINECONE_API_KEY`, `PINECONE_ENV`, `OPENAI_API_KEY` (or Claude key).  
3. Run `python ingestion/run_ingest.py` to load sample documents.  
4. Run `streamlit run ui/app.py` locally or follow `docs/run.md` to deploy to Cloud Run.

## Live demo
- Demo URL: _(add Cloud Run URL after deployment)_  
- Demo GIF: docs/demo.gif

## Repo layout
- `ingestion/` — document loaders, chunking, embedding scripts  
- `retrieval/` — vector DB client and similarity search logic  
- `src/` — orchestration and LLM prompt logic  
- `ui/` — Streamlit app for query + citation display  
- `docs/` — architecture, implement, and run documentation

## Tech stack
Pinecone/Neon, OpenAI/Claude, Streamlit, Python, Cloud Run, Buildpacks

## License
MIT
