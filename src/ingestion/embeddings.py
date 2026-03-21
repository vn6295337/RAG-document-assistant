# src/ingestion/embeddings.py
"""
Lean Embedding generation for RAG pipeline using AWS Bedrock.
"""

import hashlib
import struct
import json
import os
from typing import List, Dict, Optional

def _get_bedrock_embedding(text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> List[float]:
    """
    Get embedding from AWS Bedrock (Native).
    """
    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        bedrock = boto3.client(service_name="bedrock-runtime", region_name=region)
        
        # Titan v2 supports 256, 512, 1024 dimensions
        payload = {
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        }
        
        response = bedrock.invoke_model(
            body=json.dumps(payload),
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get("body").read())
        return response_body.get("embedding", [])
    except Exception as e:
        raise RuntimeError(f"Bedrock embedding failed: {str(e)}")

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
    Lean provider getter. Default is now Bedrock.
    """
    if provider == "bedrock":
        return _get_bedrock_embedding(text, model_id=model_name or "amazon.titan-embed-text-v2:0")
    elif provider == "local":
        return _pseudo_vector_from_text(text, dim=dim)
    else:
        # Fallback to bedrock for any other provider in this lean version
        return _get_bedrock_embedding(text)

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
