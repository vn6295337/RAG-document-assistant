"""
BM25-based keyword search for exact term matching.

Complements semantic search by finding exact matches for:
- Error codes, IDs, version numbers
- Technical terms and acronyms
- Specific names and identifiers
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Lazy import for BM25
_bm25_index = None
_chunk_store = None
_current_chunks_path = None


@dataclass
class KeywordSearchResult:
    """Result from keyword search."""
    chunks: List[Dict[str, Any]]
    total_indexed: int


def _tokenize(text: str) -> List[str]:
    """
    Simple tokenizer for BM25 indexing.

    Converts to lowercase, splits on non-alphanumeric, filters short tokens.
    """
    if not text:
        return []
    # Lowercase and split on non-alphanumeric
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    # Keep tokens with length >= 2
    return [t for t in tokens if len(t) >= 2]


def _load_chunks(chunks_path: str = "data/chunks.jsonl") -> List[Dict[str, Any]]:
    """Load chunks from JSONL file."""
    chunks = []
    path = Path(chunks_path)

    if not path.exists():
        return chunks

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                chunks.append(chunk)
            except json.JSONDecodeError:
                continue

    return chunks


def _build_bm25_index(chunks: List[Dict[str, Any]]):
    """Build BM25 index from chunks."""
    from rank_bm25 import BM25Okapi

    # Tokenize all chunk texts
    tokenized_corpus = []
    for chunk in chunks:
        text = chunk.get("text", "")
        tokens = _tokenize(text)
        tokenized_corpus.append(tokens)

    return BM25Okapi(tokenized_corpus)


def get_bm25_index(chunks_path: str = "data/chunks.jsonl", force_rebuild: bool = False):
    """
    Get or build BM25 index (lazy singleton).

    Args:
        chunks_path: Path to chunks JSONL file
        force_rebuild: Force rebuilding the index

    Returns:
        Tuple of (BM25 index, list of chunks)
    """
    global _bm25_index, _chunk_store, _current_chunks_path

    # Rebuild if path changed, forced, or not initialized
    path_changed = _current_chunks_path != chunks_path
    if _bm25_index is None or _chunk_store is None or force_rebuild or path_changed:
        _chunk_store = _load_chunks(chunks_path)
        _current_chunks_path = chunks_path
        if _chunk_store:
            _bm25_index = _build_bm25_index(_chunk_store)
        else:
            _bm25_index = None

    return _bm25_index, _chunk_store


def reload_index(chunks_path: str = "data/chunks.jsonl") -> int:
    """
    Force reload the BM25 index from a chunks file.

    Args:
        chunks_path: Path to chunks JSONL file

    Returns:
        Number of chunks indexed
    """
    _, chunks = get_bm25_index(chunks_path, force_rebuild=True)
    return len(chunks) if chunks else 0


def get_index_info() -> Dict[str, Any]:
    """
    Get information about the current BM25 index.

    Returns:
        Dict with index status information
    """
    global _bm25_index, _chunk_store, _current_chunks_path

    if _chunk_store is None:
        return {
            "loaded": False,
            "chunks": 0,
            "path": None
        }

    documents = set()
    for chunk in _chunk_store:
        documents.add(chunk.get("filename", ""))

    return {
        "loaded": True,
        "chunks": len(_chunk_store),
        "documents": len(documents),
        "path": _current_chunks_path
    }


def keyword_search(
    query: str,
    top_k: int = 10,
    chunks_path: str = "data/chunks.jsonl"
) -> KeywordSearchResult:
    """
    Search chunks using BM25 keyword matching.

    Args:
        query: Search query
        top_k: Number of results to return
        chunks_path: Path to chunks JSONL file

    Returns:
        KeywordSearchResult with matching chunks and metadata
    """
    bm25, chunks = get_bm25_index(chunks_path)

    if bm25 is None or not chunks:
        return KeywordSearchResult(chunks=[], total_indexed=0)

    # Tokenize query
    query_tokens = _tokenize(query)

    if not query_tokens:
        return KeywordSearchResult(chunks=[], total_indexed=len(chunks))

    # Get BM25 scores
    scores = bm25.get_scores(query_tokens)

    # Get top-k indices
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    # Build results
    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Only include if there's some match
            chunk = chunks[idx].copy()
            chunk["bm25_score"] = float(scores[idx])
            chunk["score"] = float(scores[idx])  # Unified score field
            results.append(chunk)

    return KeywordSearchResult(chunks=results, total_indexed=len(chunks))


def hybrid_score_chunks(
    semantic_chunks: List[Dict[str, Any]],
    keyword_chunks: List[Dict[str, Any]],
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Combine semantic and keyword search results using weighted RRF.

    Args:
        semantic_chunks: Results from semantic search
        keyword_chunks: Results from keyword search
        semantic_weight: Weight for semantic results (0-1)
        keyword_weight: Weight for keyword results (0-1)
        top_k: Number of results to return

    Returns:
        Combined and reranked list of chunks
    """
    # RRF constant
    k = 60

    # Calculate RRF scores
    chunk_scores: Dict[str, float] = {}
    chunk_data: Dict[str, Dict[str, Any]] = {}

    # Process semantic results
    for rank, chunk in enumerate(semantic_chunks):
        chunk_id = chunk.get("id", "")
        if not chunk_id:
            continue
        rrf = semantic_weight * (1.0 / (k + rank + 1))
        chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = chunk.copy()
            chunk_data[chunk_id]["search_sources"] = ["semantic"]
        else:
            chunk_data[chunk_id]["search_sources"].append("semantic")

    # Process keyword results
    for rank, chunk in enumerate(keyword_chunks):
        chunk_id = chunk.get("id", "")
        if not chunk_id:
            continue
        rrf = keyword_weight * (1.0 / (k + rank + 1))
        chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = chunk.copy()
            chunk_data[chunk_id]["search_sources"] = ["keyword"]
        else:
            if "keyword" not in chunk_data[chunk_id].get("search_sources", []):
                chunk_data[chunk_id]["search_sources"].append("keyword")

    # Sort by combined score
    sorted_ids = sorted(chunk_scores.keys(), key=lambda x: chunk_scores[x], reverse=True)

    # Build final results
    results = []
    for chunk_id in sorted_ids[:top_k]:
        chunk = chunk_data[chunk_id]
        chunk["hybrid_score"] = chunk_scores[chunk_id]
        results.append(chunk)

    return results
