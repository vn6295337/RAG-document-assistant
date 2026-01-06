"""
CLI utility for testing Pinecone retrieval.

Usage:
    python tests/test_retrieval.py "your query text"

Note: Core retrieval logic has been moved to src/retrieval/retriever.py
This file is now just a thin CLI wrapper for manual testing.
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retrieval.retriever import query_pinecone

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tests/test_retrieval.py \"your query text\"")
        sys.exit(2)
    q = sys.argv[1]
    hits = query_pinecone(q, top_k=5)
    print(json.dumps({"query": q, "results": hits}, indent=2))
