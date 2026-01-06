"""
Hybrid retrieval combining semantic and keyword search.

Provides better recall by leveraging both:
- Semantic search: conceptual similarity
- Keyword search: exact term matching
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.retrieval.retriever import query_pinecone
from src.retrieval.keyword_search import keyword_search, hybrid_score_chunks


@dataclass
class HybridSearchResult:
    """Result from hybrid search."""
    chunks: List[Dict[str, Any]]
    semantic_count: int
    keyword_count: int
    strategy: str


def hybrid_search(
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    fetch_k: int = None,
    chunks_path: str = "data/chunks.jsonl"
) -> HybridSearchResult:
    """
    Perform hybrid search combining semantic and keyword retrieval.

    Args:
        query: Search query
        top_k: Final number of results to return
        semantic_weight: Weight for semantic search results (0-1)
        keyword_weight: Weight for keyword search results (0-1)
        fetch_k: Number to fetch from each source (default: 2x top_k)
        chunks_path: Path to chunks file for BM25

    Returns:
        HybridSearchResult with combined chunks and metadata
    """
    if fetch_k is None:
        fetch_k = top_k * 2

    semantic_chunks = []
    keyword_chunks = []

    # 1. Semantic search via Pinecone
    try:
        semantic_results = query_pinecone(query, top_k=fetch_k)
        # Ensure chunks have text field from metadata if not present
        for chunk in semantic_results:
            if "text" not in chunk and "metadata" in chunk:
                chunk["text"] = chunk["metadata"].get("text", "")
        semantic_chunks = semantic_results
    except Exception:
        semantic_chunks = []

    # 2. Keyword search via BM25
    try:
        keyword_result = keyword_search(query, top_k=fetch_k, chunks_path=chunks_path)
        keyword_chunks = keyword_result.chunks
    except Exception:
        keyword_chunks = []

    # 3. Determine strategy based on what succeeded
    if semantic_chunks and keyword_chunks:
        strategy = "hybrid"
        combined = hybrid_score_chunks(
            semantic_chunks=semantic_chunks,
            keyword_chunks=keyword_chunks,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            top_k=top_k
        )
    elif semantic_chunks:
        strategy = "semantic_only"
        combined = semantic_chunks[:top_k]
    elif keyword_chunks:
        strategy = "keyword_only"
        combined = keyword_chunks[:top_k]
    else:
        strategy = "none"
        combined = []

    return HybridSearchResult(
        chunks=combined,
        semantic_count=len(semantic_chunks),
        keyword_count=len(keyword_chunks),
        strategy=strategy
    )
