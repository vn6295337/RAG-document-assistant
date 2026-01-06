"""
Reranking module for improving retrieval precision.

Uses cross-encoder models to reorder initial retrieval results
based on query-document relevance.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Model cache for lazy loading
_reranker_model = None
_reranker_model_name = None


@dataclass
class RerankResult:
    """Result from reranking operation."""
    chunks: List[Dict[str, Any]]
    model_used: str
    reranked: bool


def _get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """
    Lazy load and cache cross-encoder model.

    Args:
        model_name: HuggingFace model name for cross-encoder

    Returns:
        CrossEncoder model instance
    """
    global _reranker_model, _reranker_model_name

    if _reranker_model is None or _reranker_model_name != model_name:
        try:
            from sentence_transformers import CrossEncoder
            _reranker_model = CrossEncoder(model_name)
            _reranker_model_name = model_name
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load cross-encoder model: {e}")

    return _reranker_model


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
) -> RerankResult:
    """
    Rerank chunks using a cross-encoder model.

    Cross-encoders process query and document together, enabling
    more nuanced relevance scoring than bi-encoders.

    Args:
        query: User query
        chunks: List of chunks to rerank
        top_k: Number of top results to return
        model_name: Cross-encoder model to use

    Returns:
        RerankResult with reranked chunks
    """
    if not chunks:
        return RerankResult(chunks=[], model_used="none", reranked=False)

    if len(chunks) <= 1:
        return RerankResult(chunks=chunks, model_used="none", reranked=False)

    try:
        model = _get_cross_encoder(model_name)

        # Prepare query-document pairs
        pairs = []
        for chunk in chunks:
            text = chunk.get("text", "")
            if not text and "metadata" in chunk:
                text = chunk["metadata"].get("text", "")
            pairs.append((query, text))

        # Get relevance scores
        scores = model.predict(pairs)

        # Combine chunks with scores and sort
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Build result with rerank scores
        results = []
        for chunk, score in scored_chunks[:top_k]:
            result_chunk = chunk.copy()
            result_chunk["rerank_score"] = float(score)
            results.append(result_chunk)

        return RerankResult(
            chunks=results,
            model_used=model_name,
            reranked=True
        )

    except Exception as e:
        # Fallback: return original chunks without reranking
        return RerankResult(
            chunks=chunks[:top_k],
            model_used=f"fallback (error: {str(e)[:50]})",
            reranked=False
        )


def rerank_with_llm(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> RerankResult:
    """
    Rerank chunks using LLM-based scoring (fallback method).

    More expensive but works without additional models.

    Args:
        query: User query
        chunks: List of chunks to rerank
        top_k: Number of top results to return

    Returns:
        RerankResult with reranked chunks
    """
    if not chunks:
        return RerankResult(chunks=[], model_used="none", reranked=False)

    if len(chunks) <= 1:
        return RerankResult(chunks=chunks, model_used="none", reranked=False)

    try:
        from src.llm_providers import call_llm

        # Build scoring prompt
        chunk_texts = []
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")[:500]  # Truncate for prompt size
            chunk_texts.append(f"[{i}] {text}")

        prompt = f"""Rate the relevance of each document to the query on a scale of 0-10.
Return ONLY a comma-separated list of scores in order (e.g., "8,3,7,5").

Query: {query}

Documents:
{chr(10).join(chunk_texts)}

Scores:"""

        response = call_llm(prompt=prompt, temperature=0.0, max_tokens=100)
        scores_text = response.get("text", "").strip()

        # Parse scores
        try:
            scores = [float(s.strip()) for s in scores_text.split(",")]
            if len(scores) != len(chunks):
                raise ValueError("Score count mismatch")
        except (ValueError, AttributeError):
            # Fallback to original order
            return RerankResult(
                chunks=chunks[:top_k],
                model_used="llm_parse_failed",
                reranked=False
            )

        # Sort by scores
        scored_chunks = list(zip(chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        results = []
        for chunk, score in scored_chunks[:top_k]:
            result_chunk = chunk.copy()
            result_chunk["rerank_score"] = float(score)
            results.append(result_chunk)

        return RerankResult(
            chunks=results,
            model_used="llm",
            reranked=True
        )

    except Exception as e:
        return RerankResult(
            chunks=chunks[:top_k],
            model_used=f"llm_fallback (error: {str(e)[:50]})",
            reranked=False
        )
