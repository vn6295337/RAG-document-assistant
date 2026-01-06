# RAG-document-assistant/scripts/search_documents.py
"""
Local similarity search (cosine) over embeddings.jsonl.

Purpose:
    Performs local similarity search using cosine similarity over pre-generated embeddings.
    Useful for testing and debugging search functionality without connecting to a vector database.

Inputs:
    embeddings_path (str): Path to embeddings.jsonl file
    query (str): Search query text
    k (int, optional): Number of results to return (default: 3)
    dim (int, optional): Embedding dimension (default: 64)

Outputs:
    Prints top-k results with id, filename, chunk_id, and similarity score

Usage:
    python scripts/search_documents.py /path/to/embeddings.jsonl "query text" [k] [dim]

Example:
    python scripts/search_documents.py ./data/chunks.jsonl "what is GDPR" 5 384
"""

import sys
import json
import math
from pathlib import Path
from typing import List
from src.ingestion.embeddings import get_embedding

def load_embeddings(path: str):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    items = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            items.append(obj)
    return items

def dot(a: List[float], b: List[float]) -> float:
    return sum(x*y for x,y in zip(a,b))

def norm(a: List[float]) -> float:
    return math.sqrt(sum(x*x for x in a))

def cosine_sim(a: List[float], b: List[float]) -> float:
    na = norm(a)
    nb = norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a,b) / (na * nb)

def search(embeddings_path: str, query: str, k: int = 3, dim: int = 64):
    items = load_embeddings(embeddings_path)
    qvec = get_embedding(query, provider="local", dim=dim)
    scored = []
    for it in items:
        emb = it.get("embedding")
        if not emb:
            continue
        score = cosine_sim(qvec, emb)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]

def print_results(results):
    print(f"{'SCORE':>8}  {'ID':60}  {'FILENAME':40}  {'CHUNK_ID':>7}")
    print("-"*130)
    for score, it in results:
        print(f"{score:8.4f}  {it['id'][:60]:60}  {it['filename'][:40]:40}  {it['chunk_id']:7d}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/search_documents.py /path/to/embeddings.jsonl \"query text\" [k] [dim]")
        raise SystemExit(1)
    emb_path = sys.argv[1]
    query = sys.argv[2]
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    dim = int(sys.argv[4]) if len(sys.argv) > 4 else 64

    results = search(emb_path, query, k=k, dim=dim)
    print_results(results)