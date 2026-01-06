"""
Context shaping module for optimizing retrieved chunks.

Performs:
- Deduplication: Remove semantically similar chunks
- Token budgeting: Allocate tokens based on relevance
- Pruning: Remove irrelevant sentences within chunks
- Compression: Summarize if over budget
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import re

# Lazy imports
_sentence_model = None


@dataclass
class ContextShapeResult:
    """Result of context shaping."""
    chunks: List[Dict[str, Any]]
    original_tokens: int
    final_tokens: int
    chunks_removed: int
    compression_applied: bool


def _estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 1 token ≈ 4 chars)."""
    return len(text) // 4


def _get_sentence_model():
    """Lazy load sentence transformer for similarity."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            return None
    return _sentence_model


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two texts."""
    model = _get_sentence_model()
    if model is None:
        return 0.0

    try:
        import numpy as np
        embeddings = model.encode([text1, text2])
        cos_sim = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(cos_sim)
    except Exception:
        return 0.0


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def deduplicate_chunks(
    chunks: List[Dict[str, Any]],
    threshold: float = 0.85
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Remove chunks with high semantic similarity.

    Args:
        chunks: List of chunks
        threshold: Similarity threshold for deduplication

    Returns:
        Tuple of (deduplicated chunks, count removed)
    """
    if len(chunks) <= 1:
        return chunks, 0

    # Keep track of which chunks to keep
    keep_indices = []
    removed = 0

    for i, chunk in enumerate(chunks):
        text_i = chunk.get("text", "")
        is_duplicate = False

        # Compare with already kept chunks
        for j in keep_indices:
            text_j = chunks[j].get("text", "")
            similarity = _compute_similarity(text_i, text_j)

            if similarity >= threshold:
                is_duplicate = True
                removed += 1
                break

        if not is_duplicate:
            keep_indices.append(i)

    return [chunks[i] for i in keep_indices], removed


def budget_chunks(
    chunks: List[Dict[str, Any]],
    token_budget: int,
    min_tokens_per_chunk: int = 50
) -> List[Dict[str, Any]]:
    """
    Allocate token budget across chunks based on relevance scores.

    Args:
        chunks: List of chunks with scores
        token_budget: Total token budget
        min_tokens_per_chunk: Minimum tokens to keep per chunk

    Returns:
        Chunks with text trimmed to fit budget
    """
    if not chunks:
        return []

    # Calculate total relevance for weighting
    total_score = sum(c.get("score", 0.5) for c in chunks)
    if total_score == 0:
        total_score = len(chunks)  # Equal weight

    budgeted = []
    remaining_budget = token_budget

    for chunk in chunks:
        text = chunk.get("text", "")
        score = chunk.get("score", 0.5)

        # Allocate budget proportionally to score
        chunk_budget = int((score / total_score) * token_budget)
        chunk_budget = max(chunk_budget, min_tokens_per_chunk)
        chunk_budget = min(chunk_budget, remaining_budget)

        if chunk_budget <= 0:
            continue

        # Trim text if needed
        current_tokens = _estimate_tokens(text)
        if current_tokens > chunk_budget:
            # Truncate to fit budget (keep first N chars)
            char_limit = chunk_budget * 4
            text = text[:char_limit].rsplit(" ", 1)[0] + "..."

        new_chunk = chunk.copy()
        new_chunk["text"] = text
        new_chunk["budget_allocated"] = chunk_budget
        budgeted.append(new_chunk)

        remaining_budget -= _estimate_tokens(text)
        if remaining_budget <= 0:
            break

    return budgeted


def prune_irrelevant_sentences(
    chunk: Dict[str, Any],
    query: str,
    relevance_threshold: float = 0.3
) -> Dict[str, Any]:
    """
    Remove sentences within a chunk that are not relevant to the query.

    Args:
        chunk: Chunk to prune
        query: Query for relevance comparison
        relevance_threshold: Minimum similarity to keep sentence

    Returns:
        Chunk with irrelevant sentences removed
    """
    text = chunk.get("text", "")
    if not text:
        return chunk

    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return chunk

    # Score each sentence
    relevant_sentences = []
    for sentence in sentences:
        if len(sentence) < 10:  # Keep short fragments
            relevant_sentences.append(sentence)
            continue

        similarity = _compute_similarity(query, sentence)
        if similarity >= relevance_threshold:
            relevant_sentences.append(sentence)

    if not relevant_sentences:
        # Keep at least the first sentence
        relevant_sentences = sentences[:1]

    new_chunk = chunk.copy()
    new_chunk["text"] = " ".join(relevant_sentences)
    new_chunk["sentences_pruned"] = len(sentences) - len(relevant_sentences)
    return new_chunk


def compress_with_llm(
    chunks: List[Dict[str, Any]],
    query: str,
    target_tokens: int
) -> List[Dict[str, Any]]:
    """
    Compress chunks using LLM summarization.

    Args:
        chunks: Chunks to compress
        query: Query for context-aware compression
        target_tokens: Target token count

    Returns:
        Compressed chunks
    """
    try:
        from src.llm_providers import call_llm
    except ImportError:
        return chunks

    # Combine all chunk texts
    combined = "\n\n".join(c.get("text", "") for c in chunks)
    current_tokens = _estimate_tokens(combined)

    if current_tokens <= target_tokens:
        return chunks

    prompt = f"""Summarize the following context to approximately {target_tokens * 4} characters.
Preserve all key facts relevant to this query: {query}
Keep specific names, numbers, and dates.

Context:
{combined}

Summary:"""

    try:
        response = call_llm(prompt=prompt, temperature=0.0, max_tokens=target_tokens)
        summary = response.get("text", "").strip()

        # Return as single compressed chunk
        return [{
            "id": "compressed_context",
            "text": summary,
            "score": max(c.get("score", 0) for c in chunks),
            "compressed_from": len(chunks)
        }]
    except Exception:
        return chunks


def shape_context(
    chunks: List[Dict[str, Any]],
    query: str,
    token_budget: int = 3000,
    dedup_threshold: float = 0.85,
    enable_pruning: bool = True,
    enable_compression: bool = True,
    relevance_threshold: float = 0.3
) -> ContextShapeResult:
    """
    Shape context by deduplicating, pruning, and compressing chunks.

    Args:
        chunks: Retrieved chunks
        query: User query for relevance
        token_budget: Maximum tokens for final context
        dedup_threshold: Similarity threshold for deduplication
        enable_pruning: Whether to prune irrelevant sentences
        enable_compression: Whether to compress if over budget
        relevance_threshold: Minimum relevance for sentence pruning

    Returns:
        ContextShapeResult with shaped chunks and metadata
    """
    if not chunks:
        return ContextShapeResult(
            chunks=[],
            original_tokens=0,
            final_tokens=0,
            chunks_removed=0,
            compression_applied=False
        )

    # Calculate original token count
    original_tokens = sum(_estimate_tokens(c.get("text", "")) for c in chunks)

    # Step 1: Deduplicate
    deduped, removed = deduplicate_chunks(chunks, threshold=dedup_threshold)

    # Step 2: Prune irrelevant sentences (optional)
    if enable_pruning:
        deduped = [
            prune_irrelevant_sentences(c, query, relevance_threshold)
            for c in deduped
        ]

    # Step 3: Budget allocation
    budgeted = budget_chunks(deduped, token_budget)

    # Step 4: Check if compression needed
    current_tokens = sum(_estimate_tokens(c.get("text", "")) for c in budgeted)
    compression_applied = False

    if enable_compression and current_tokens > token_budget * 1.2:
        budgeted = compress_with_llm(budgeted, query, token_budget)
        compression_applied = True

    final_tokens = sum(_estimate_tokens(c.get("text", "")) for c in budgeted)

    return ContextShapeResult(
        chunks=budgeted,
        original_tokens=original_tokens,
        final_tokens=final_tokens,
        chunks_removed=removed,
        compression_applied=compression_applied
    )
