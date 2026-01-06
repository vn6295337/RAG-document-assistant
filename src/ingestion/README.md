# RAG PoC — Ingestion

This folder contains Day-3 ingestion pipeline components.

Files:
- load_docs.py        : Markdown loader -> returns cleaned text + metadata
- chunker.py          : Deterministic whitespace chunker (approx tokens->chars)
- test_ingestion.py   : End-to-end loader -> chunker smoke test
- embeddings.py       : Offline deterministic pseudo-embedding stub (provider="local")
- save_embeddings.py  : Persist chunk embeddings to data/embeddings.jsonl
- search_local.py     : Local cosine-similarity retrieval against embeddings.jsonl
- data/embeddings.jsonl : Generated embeddings (JSONL)

Quick run (from `RAG-document-assistant/ingestion`, with `aienv` active):

1. Activate venv:
   source ~/aienv/bin/activate

2. Load & summarize docs:
   python3 load_docs.py /full/path/to/your/markdown_folder

3. End-to-end ingestion test:
   python3 test_ingestion.py /full/path/to/your/markdown_folder

4. Generate & save embeddings:
   python3 save_embeddings.py /full/path/to/your/markdown_folder local 64

5. Search locally:
   python3 search_local.py data/embeddings.jsonl "your query" 3 64

Notes:
- Replace `/full/path/to/your/markdown_folder` with your real path (e.g. /home/vn6295337/RAG-document-assistant/sample_docs).
- This pipeline uses a local pseudo-embedding for offline testing. Replace provider branches when ready to use real APIs.