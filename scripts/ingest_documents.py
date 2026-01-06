"""
Day-3 → Day-4 bridge ingestion script.

Purpose:
    Runs the full document ingestion pipeline including loading documents, chunking them,
    generating embeddings, and saving the results to a file. Used for processing documents
    that will later be uploaded to a vector database.

Pipeline:
1. Load markdown docs
2. Chunk them
3. Generate embeddings (local stub for now)
4. Save to chunks.jsonl file

Inputs:
    docs_dir (str): Path to directory containing markdown documents
    provider (str, optional): Embedding provider (default: "local")
    dim (int, optional): Embedding dimension (default: 128)
    save_to (str, optional): Path to save chunks.jsonl file

Outputs:
    Saves embedded chunks to specified file
    Returns list of embedded chunks with metadata

Usage:
    python scripts/ingest_documents.py /path/to/docs [provider] [dim]

Example:
    python scripts/ingest_documents.py ./sample_docs sentence-transformers 384
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.load_docs import load_markdown_docs
from src.ingestion.chunker import chunk_documents
from src.ingestion.embeddings import batch_embed_chunks

def run_ingestion(docs_dir: str, provider: str = "local", dim: int = 128, save_to: str = None):
    """
    Run full ingestion pipeline: load docs -> chunk -> embed -> optionally save

    Args:
        docs_dir: Path to directory containing markdown docs
        provider: Embedding provider (default: "local")
        dim: Embedding dimension (default: 128)
        save_to: Optional path to save chunks.jsonl file

    Returns:
        List of embedded chunks with metadata
    """
    import json

    docs = load_markdown_docs(docs_dir)
    chunks = chunk_documents(docs, max_tokens=300, overlap=50)
    embedded = batch_embed_chunks(chunks, provider=provider, dim=dim)

    # Merge text back into embedded chunks (embeddings.py strips it)
    chunk_map = {(c["filename"], c["chunk_id"]): c["text"] for c in chunks}
    for e in embedded:
        key = (e["filename"], e["chunk_id"])
        if key in chunk_map:
            e["text"] = chunk_map[key]

    # Save to file if requested
    if save_to:
        save_path = Path(save_to)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with save_path.open("w", encoding="utf-8") as fh:
            for e in embedded:
                obj = {
                    "id": f"{e['filename']}::{e['chunk_id']}",
                    "filename": e["filename"],
                    "chunk_id": e["chunk_id"],
                    "text": e.get("text", ""),
                    "chars": e.get("chars", 0),
                    "embedding": e["embedding"]
                }
                fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print(f"Saved {len(embedded)} chunks to: {save_to}")

    return embedded

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/ingest_documents.py /path/to/docs [provider] [dim]")
        raise SystemExit(1)

    docs_dir = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "local"
    dim = int(sys.argv[3]) if len(sys.argv) > 3 else 128

    # Save to data/chunks.jsonl by default
    save_path = str(PROJECT_ROOT / "data" / "chunks.jsonl")

    out = run_ingestion(docs_dir, provider=provider, dim=dim, save_to=save_path)
    print(f"Total embedded chunks: {len(out)}")