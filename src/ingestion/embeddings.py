# RAG-document-assistant/ingestion/embeddings.py
"""
Embedding generation for RAG pipeline.

Supported providers:
- "local": Deterministic hash-based embeddings (testing only)
- "sentence-transformers": Free semantic embeddings using HuggingFace models
- "openai", "claude": Placeholders for future API-based embeddings

Default model: all-MiniLM-L6-v2 (384 dimensions, good balance of speed/quality)
"""

import hashlib
import struct
from typing import List, Dict, Optional

# Lazy-load sentence-transformers to avoid import errors if not installed
_MODEL_CACHE = {}

def _get_sentence_transformer_model(model_name: str = "all-MiniLM-L6-v2"):
    """Lazy load and cache sentence transformer model."""
    if model_name not in _MODEL_CACHE:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    return _MODEL_CACHE[model_name]

def _pseudo_vector_from_text(text: str, dim: int = 128) -> List[float]:
    """
    Deterministic pseudo-embedding: hash the text and expand into floats.
    Not a real embedding — used for pipeline testing.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    # expand by repeating hash bytes to reach dim; convert to float in [0,1)
    i = 0
    while len(vec) < dim:
        # take 4 bytes -> float
        chunk = h[i % len(h):(i % len(h)) + 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\0")
        val = struct.unpack("I", chunk)[0] / 2**32
        vec.append(float(val))
        i += 4
    return vec[:dim]

def get_embedding(
    text: str,
    provider: str = "local",
    dim: int = 128,
    model_name: Optional[str] = None
) -> List[float]:
    """
    Provider-agnostic embedding getter.

    Args:
        text: Text to embed
        provider: "local" | "sentence-transformers" | "openai" | "claude"
        dim: Dimension for local embeddings (ignored for other providers)
        model_name: Optional model name for sentence-transformers

    Returns:
        List of floats representing the embedding vector
        
    Raises:
        ValueError: If provider is unknown or text is empty
        ImportError: If required dependencies are not installed
        NotImplementedError: If provider is not yet implemented
        Exception: If embedding generation fails
    """
    if not text:
        raise ValueError("text cannot be empty")
        
    provider = provider.lower()

    if provider == "local":
        return _pseudo_vector_from_text(text, dim=dim)

    elif provider == "sentence-transformers":
        model = _get_sentence_transformer_model(model_name or "all-MiniLM-L6-v2")
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding with sentence-transformers: {str(e)}")

    elif provider in ("openai", "claude"):
        raise NotImplementedError(f"Provider '{provider}' is not configured yet.")

    else:
        raise ValueError(f"Unknown provider: {provider}")

def batch_embed_chunks(
    chunks: List[Dict],
    provider: str = "local",
    dim: int = 128,
    model_name: Optional[str] = None
) -> List[Dict]:
    """
    Batch embed multiple chunks.
    
    Args:
        chunks: List of dicts with "filename", "chunk_id", "text", "chars"
        provider: Embedding provider
        dim: Dimension for local embeddings
        model_name: Optional model name for sentence-transformers
        
    Returns:
        List of dicts with "filename", "chunk_id", "embedding", "chars"
        
    Raises:
        TypeError: If chunks is not a list or contains non-dict elements
        KeyError: If required keys are missing from chunk dictionaries
        ValueError: If provider is unknown or dim is not positive
        ImportError: If required dependencies are not installed
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")
        
    # Validate chunks
    for i, c in enumerate(chunks):
        if not isinstance(c, dict):
            raise TypeError(f"Chunk {i} is not a dictionary")
        required_keys = ["filename", "chunk_id", "text", "chars"]
        for key in required_keys:
            if key not in c:
                raise KeyError(f"Chunk {i} missing required key: {key}")
                
    if dim <= 0:
        raise ValueError(f"dim must be positive, got {dim}")
        
    # For sentence-transformers, batch encoding is more efficient
    if provider == "sentence-transformers":
        texts = [c["text"] for c in chunks]
        model = _get_sentence_transformer_model(model_name or "all-MiniLM-L6-v2")
        try:
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        except Exception as e:
            raise RuntimeError(f"Failed to encode texts with sentence-transformers: {str(e)}")
            
        # Validate embeddings shape
        if len(embeddings) != len(texts):
            raise RuntimeError(f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}")

        out = []
        for i, c in enumerate(chunks):
            out.append({
                "filename": c["filename"],
                "chunk_id": c["chunk_id"],
                "embedding": embeddings[i].tolist(),
                "chars": c["chars"]
            })
        return out

    # For other providers, embed one at a time
    out = []
    for c in chunks:
        try:
            emb = get_embedding(c["text"], provider=provider, dim=dim, model_name=model_name)
            out.append({
                "filename": c["filename"],
                "chunk_id": c["chunk_id"],
                "embedding": emb,
                "chars": c["chars"]
            })
        except Exception as e:
            raise RuntimeError(f"Failed to embed chunk {c['chunk_id']} from {c['filename']}: {str(e)}")
    return out

if __name__ == "__main__":
    # Quick local smoke test
    sample_text = "This is a test document for embedding."
    v = get_embedding(sample_text, provider="local", dim=16)
    print("Embedding length:", len(v))
    print(v[:4])