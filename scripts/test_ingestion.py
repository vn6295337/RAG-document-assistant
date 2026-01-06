# RAG-document-assistant/scripts/test_ingestion.py
"""
CLI utility for testing ingestion pipeline.

Purpose:
    Tests the document ingestion pipeline by loading documents, chunking them,
    and printing summary statistics. Does not generate embeddings or save files.

Inputs:
    docs_dir (str): Path to directory containing markdown documents

Outputs:
    Prints document and chunk counts to stdout
    Displays a sample chunk for verification

Usage:
    python scripts/test_ingestion.py <docs_dir>

Example:
    python scripts/test_ingestion.py ./sample_docs
"""

from src.ingestion.load_docs import load_markdown_docs
from src.ingestion.chunker import chunk_documents

import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_ingestion.py <docs_dir>")
        sys.exit(1)

    docs_dir = sys.argv[1]
    docs = load_markdown_docs(docs_dir)

    chunks = chunk_documents(docs, max_tokens=300, overlap=50)

    total_docs = len([d for d in docs if d.get("status") == "OK"])
    total_chunks = len(chunks)

    print(f"Docs loaded: {total_docs}")
    print(f"Chunks generated: {total_chunks}")

    # Print a sample chunk for verification
    if chunks:
        print("\nSample chunk:")
        print(chunks[0]["text"][:300])

if __name__ == "__main__":
    main()