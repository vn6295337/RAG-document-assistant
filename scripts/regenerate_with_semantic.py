#!/usr/bin/env python3
"""
Regenerate embeddings using semantic sentence-transformers model.

Purpose:
    Completely regenerates embeddings using the semantic sentence-transformers model,
    creates a new Pinecone index, and uploads the embeddings. This is a full refresh
    of the vector database with semantic embeddings.

Process:
1. Loads documents and chunks them
2. Generates semantic embeddings (384-dim using all-MiniLM-L6-v2)
3. Saves to data/chunks_semantic.jsonl
4. Creates new Pinecone index with 384 dimensions
5. Uploads semantic embeddings to new index

Inputs:
    None (uses sample_docs directory by default)
    PINECONE_API_KEY environment variable

Outputs:
    Saves embedded chunks to data/chunks_semantic.jsonl
    Creates and populates new Pinecone index
    Prints progress and completion messages

Environment variables required:
    PINECONE_API_KEY: Your Pinecone API key

Usage:
    python scripts/regenerate_with_semantic.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.load_docs import load_markdown_docs
from src.ingestion.chunker import chunk_documents
from src.ingestion.embeddings import batch_embed_chunks, get_embedding
from pinecone import Pinecone, ServerlessSpec
import src.config as cfg
import json


def main():
    print("=" * 60)
    print("Regenerating Embeddings with Semantic Model")
    print("=" * 60)

    # Step 1: Load and chunk documents
    print("\n[1/5] Loading documents...")
    docs_dir = str(PROJECT_ROOT / "sample_docs")
    docs = load_markdown_docs(docs_dir)
    print(f"   Loaded {len(docs)} documents")

    print("\n[2/5] Chunking documents...")
    chunks = chunk_documents(docs, max_tokens=300, overlap=50)
    print(f"   Generated {len(chunks)} chunks")

    # Step 2: Generate semantic embeddings
    print("\n[3/5] Generating semantic embeddings...")
    print("   Using model: all-MiniLM-L6-v2 (384 dimensions)")
    print("   This may take 1-2 minutes...")

    embedded = batch_embed_chunks(
        chunks,
        provider="sentence-transformers",
        model_name="all-MiniLM-L6-v2"
    )

    # Get actual dimension from first embedding
    actual_dim = len(embedded[0]['embedding'])
    print(f"   ✓ Generated {len(embedded)} embeddings ({actual_dim} dimensions)")

    # Step 3: Save to file
    print("\n[4/5] Saving embeddings...")
    output_file = PROJECT_ROOT / "data" / "chunks_semantic.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        for i, e in enumerate(embedded):
            # Merge text back from chunks
            chunk_text = chunks[i]["text"]
            obj = {
                "id": f"{e['filename']}::{e['chunk_id']}",
                "filename": e["filename"],
                "chunk_id": e["chunk_id"],
                "text": chunk_text,
                "chars": e.get("chars", 0),
                "embedding": e["embedding"]
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"   ✓ Saved to: {output_file}")

    # Step 4: Create new Pinecone index
    print("\n[5/5] Setting up Pinecone index...")
    print(f"   Connecting to Pinecone...")

    pc = Pinecone(api_key=cfg.PINECONE_API_KEY)

    new_index_name = "rag-semantic-384"
    print(f"   Creating new index: {new_index_name}")
    print(f"   Dimension: {actual_dim}, Metric: cosine")

    # Check if index exists
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if new_index_name in existing_indexes:
        print(f"   Index '{new_index_name}' already exists - deleting old version...")
        pc.delete_index(new_index_name)

    # Create new index
    pc.create_index(
        name=new_index_name,
        dimension=actual_dim,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print(f"   ✓ Index created")

    # Wait for index to be ready
    print("   Waiting for index to be ready...")
    import time
    while not pc.describe_index(new_index_name).status.ready:
        time.sleep(1)

    # Step 5: Upload to Pinecone
    print(f"\n   Uploading {len(embedded)} vectors to Pinecone...")

    index = pc.Index(new_index_name)

    # Prepare vectors for upsert
    vectors = []
    for e in embedded:
        vec_id = f"{e['filename']}::{e['chunk_id']}"
        vectors.append({
            "id": vec_id,
            "values": e["embedding"],
            "metadata": {}
        })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch)
        print(f"   Uploaded {min(i+batch_size, len(vectors))}/{len(vectors)} vectors")

    # Verify upload
    stats = index.describe_index_stats()
    print(f"   ✓ Index now contains {stats.total_vector_count} vectors")

    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Update config: export PINECONE_INDEX_NAME='{new_index_name}'")
    print(f"2. Test search: python -c \"from src.retrieval.retriever import query_pinecone; print(query_pinecone('what is GDPR', top_k=5))\"")
    print()


if __name__ == "__main__":
    main()