# src/ingestion/embeddings.py
"""Lean embedding generation for the RAG pipeline using AWS Bedrock."""

import hashlib
import struct
import json
import os
import time
from typing import List, Dict, Optional

def _get_bedrock_embedding(text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> List[float]:
    """
    Get embedding from AWS Bedrock (Native).
    """
    import boto3

    region = os.getenv("AWS_REGION", "us-east-1")
    max_retries = int(os.getenv("BEDROCK_EMBEDDING_MAX_RETRIES", "6"))
    backoff_seconds = float(os.getenv("BEDROCK_EMBEDDING_BACKOFF_SECONDS", "1.5"))
    dimensions = int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS", "1024"))
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", model_id)

    bedrock = boto3.client(service_name="bedrock-runtime", region_name=region)

    payload = {
        "inputText": text,
        "dimensions": dimensions,
        "normalize": True
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            response = bedrock.invoke_model(
                body=json.dumps(payload),
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get("body").read())
            return response_body.get("embedding", [])
        except Exception as e:
            last_error = e
            error_text = str(e)
            is_throttled = "ThrottlingException" in error_text or "Too many requests" in error_text
            if not is_throttled or attempt == max_retries - 1:
                break
            time.sleep(backoff_seconds * (2 ** attempt))

    raise RuntimeError(f"Bedrock embedding failed: {str(last_error)}")

def _pseudo_vector_from_text(text: str, dim: int = 128) -> List[float]:
    """Deterministic pseudo-embedding for testing."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    i = 0
    while len(vec) < dim:
        chunk = h[i % len(h):(i % len(h)) + 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\0")
        val = struct.unpack("I", chunk)[0] / 2**32
        vec.append(float(val))
        i += 4
    return vec[:dim]

def get_embedding(
    text: str,
    provider: str = "bedrock",
    dim: int = 1024,
    model_name: Optional[str] = None
) -> List[float]:
    """
    Lean provider getter.

    This AWS deployment uses Bedrock embeddings for all providers.
    Legacy provider labels are accepted for compatibility and mapped to Bedrock.
    """
    return _get_bedrock_embedding(
        text, model_id=model_name or "amazon.titan-embed-text-v2:0"
    )

def batch_embed_chunks(
    chunks: List[Dict],
    provider: str = "bedrock",
    dim: int = 1024
) -> List[Dict]:
    """Process multiple chunks."""
    for chunk in chunks:
        text = chunk.get("text", "")
        if text:
            chunk["embedding"] = get_embedding(text, provider=provider, dim=dim)
        else:
            chunk["embedding"] = [0.0] * dim
    return chunks
