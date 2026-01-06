"""
Ingestion API for UI integration.

Provides functions to ingest documents from a directory
and optionally sync to Pinecone.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.ingestion.load_docs import load_markdown_docs
from src.ingestion.chunker import chunk_documents
from src.ingestion.embeddings import batch_embed_chunks


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    status: str
    documents: int
    chunks: int
    output_path: str
    errors: List[str]


@dataclass
class SyncResult:
    """Result of Pinecone sync."""
    status: str
    vectors_upserted: int
    errors: List[str]


def ingest_from_directory(
    docs_dir: str,
    output_path: str = "data/chunks.jsonl",
    provider: str = "sentence-transformers",
    dim: int = 384
) -> IngestionResult:
    """
    Ingest documents from a directory and save to chunks.jsonl.

    Args:
        docs_dir: Path to directory containing documents
        output_path: Path to save chunks.jsonl
        provider: Embedding provider ("sentence-transformers" or "local")
        dim: Embedding dimension

    Returns:
        IngestionResult with status and counts
    """
    errors = []

    # Validate directory
    if not os.path.isdir(docs_dir):
        return IngestionResult(
            status="error",
            documents=0,
            chunks=0,
            output_path=output_path,
            errors=[f"Directory not found: {docs_dir}"]
        )

    try:
        # Load documents
        docs = load_markdown_docs(docs_dir)
        if not docs:
            return IngestionResult(
                status="warning",
                documents=0,
                chunks=0,
                output_path=output_path,
                errors=["No documents found in directory"]
            )

        # Count successful loads
        doc_count = len([d for d in docs if d.get("status") == "ok"])

        # Chunk documents
        chunks = chunk_documents(docs, max_tokens=300, overlap=50)
        if not chunks:
            return IngestionResult(
                status="warning",
                documents=doc_count,
                chunks=0,
                output_path=output_path,
                errors=["No chunks generated from documents"]
            )

        # Generate embeddings
        embedded = batch_embed_chunks(chunks, provider=provider, dim=dim)

        # Merge text back into embedded chunks
        chunk_map = {(c["filename"], c["chunk_id"]): c["text"] for c in chunks}
        for e in embedded:
            key = (e["filename"], e["chunk_id"])
            if key in chunk_map:
                e["text"] = chunk_map[key]

        # Save to file
        save_path = Path(output_path)
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

        return IngestionResult(
            status="success",
            documents=doc_count,
            chunks=len(embedded),
            output_path=output_path,
            errors=errors
        )

    except Exception as e:
        return IngestionResult(
            status="error",
            documents=0,
            chunks=0,
            output_path=output_path,
            errors=[str(e)]
        )


def sync_to_pinecone(
    chunks_path: str = "data/chunks.jsonl",
    index_name: str = None,
    batch_size: int = 100
) -> SyncResult:
    """
    Upload embeddings from chunks.jsonl to Pinecone.

    Args:
        chunks_path: Path to chunks.jsonl file
        index_name: Pinecone index name (uses config default if None)
        batch_size: Number of vectors to upsert per batch

    Returns:
        SyncResult with status and count
    """
    errors = []

    # Validate file exists
    if not os.path.isfile(chunks_path):
        return SyncResult(
            status="error",
            vectors_upserted=0,
            errors=[f"Chunks file not found: {chunks_path}"]
        )

    try:
        # Load Pinecone config
        import src.config as cfg
        from pinecone import Pinecone

        if index_name is None:
            index_name = cfg.PINECONE_INDEX_NAME

        # Initialize Pinecone
        pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
        idx_meta = pc.describe_index(index_name)

        # Get host
        host = getattr(idx_meta, "host", None) or idx_meta.get("host")
        if not host:
            return SyncResult(
                status="error",
                vectors_upserted=0,
                errors=[f"Could not get host for index: {index_name}"]
            )

        index = pc.Index(host=host)

        # Load chunks
        chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))

        if not chunks:
            return SyncResult(
                status="warning",
                vectors_upserted=0,
                errors=["No chunks to upload"]
            )

        # Prepare vectors
        vectors = []
        for chunk in chunks:
            embedding = chunk.get("embedding", [])
            if not embedding:
                continue

            vectors.append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": {
                    "filename": chunk.get("filename", ""),
                    "chunk_id": chunk.get("chunk_id", 0),
                    "text": chunk.get("text", "")[:1000]  # Limit metadata size
                }
            })

        # Upsert in batches
        upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            try:
                index.upsert(vectors=batch)
                upserted += len(batch)
            except Exception as e:
                errors.append(f"Batch {i // batch_size} failed: {str(e)[:100]}")

        return SyncResult(
            status="success" if not errors else "partial",
            vectors_upserted=upserted,
            errors=errors
        )

    except Exception as e:
        return SyncResult(
            status="error",
            vectors_upserted=0,
            errors=[str(e)]
        )


def get_index_status(chunks_path: str = "data/chunks.jsonl") -> Dict[str, Any]:
    """
    Get status of the current index.

    Args:
        chunks_path: Path to chunks.jsonl file

    Returns:
        Dict with chunk count, document count, and file info
    """
    if not os.path.isfile(chunks_path):
        return {
            "exists": False,
            "chunks": 0,
            "documents": 0,
            "path": chunks_path
        }

    try:
        chunks = 0
        documents = set()

        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    chunks += 1
                    documents.add(obj.get("filename", ""))

        return {
            "exists": True,
            "chunks": chunks,
            "documents": len(documents),
            "path": chunks_path
        }

    except Exception as e:
        return {
            "exists": True,
            "chunks": 0,
            "documents": 0,
            "path": chunks_path,
            "error": str(e)
        }
