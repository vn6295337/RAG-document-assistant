# RAG-document-assistant/ingestion/save_embeddings.py
"""
Persist chunk embeddings to a local JSONL file for later import.
Outputs: RAG-document-assistant/ingestion/data/embeddings.jsonl
Each line is a JSON object:
{
  "id": "<filename>::<chunk_id>",
  "filename": "<filename>",
  "chunk_id": <int>,
  "text": "<first_250_chars_of_chunk>",
  "chars": <int>,
  "embedding": [float,...]
}
"""

import os
import json
from pathlib import Path
from load_docs import load_markdown_docs
from chunker import chunk_documents
from embeddings import batch_embed_chunks

OUT_DIR = Path(__file__).resolve().parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "embeddings.jsonl"

def run(docs_dir: str, provider: str = "local", dim: int = 128):
    docs = load_markdown_docs(docs_dir)
    chunks = chunk_documents(docs, max_tokens=300, overlap=50)
    embedded = batch_embed_chunks(chunks, provider=provider, dim=dim)

    with OUT_FILE.open("w", encoding="utf-8") as fh:
        for e in embedded:
            obj = {
                "id": f"{e['filename']}::{e['chunk_id']}",
                "filename": e["filename"],
                "chunk_id": e["chunk_id"],
                "text": (e.get("text") or "")[:250],
                "chars": e.get("chars", 0),
                "embedding": e["embedding"]
            }
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return OUT_FILE

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 save_embeddings.py /full/path/to/docs_dir [provider] [dim]")
        raise SystemExit(1)
    docs_dir = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "local"
    dim = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    out = run(docs_dir, provider=provider, dim=dim)
    print("Wrote embeddings file:", out)
