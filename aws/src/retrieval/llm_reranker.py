# src/retrieval/llm_reranker.py
"""LLM-based reranking for improved retrieval precision."""

import logging
import re
from typing import List, Dict, Any, Optional
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMRerankResult:
    """Result of LLM-based reranking."""
    chunks: List[Dict[str, Any]]
    reranked: bool
    model_used: str
    reasoning: Optional[str] = None


RERANK_PROMPT = """You are a relevance judge. Given a query and a list of text passages, rank them by relevance to the query.

Query: {query}

Passages:
{passages}

Return a JSON array of passage IDs ordered from most to least relevant. Only include the IDs.
Example: ["id1", "id3", "id2"]

Ranked IDs:"""


RERANK_WITH_REASONING_PROMPT = """You are a relevance judge. Given a query and a list of text passages, rank them by relevance.

Query: {query}

Passages:
{passages}

For each passage, briefly explain its relevance, then provide the final ranking.

Format:
REASONING:
- [id]: <brief relevance explanation>
...

RANKING: ["most_relevant_id", "second_id", ...]

Response:"""


def llm_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    provider: str = None,
    model: str = None,
    with_reasoning: bool = False
) -> LLMRerankResult:
    """
    Rerank chunks using LLM-based relevance judgment.

    This is more expensive than cross-encoder but can be more accurate
    for nuanced relevance judgments.

    Args:
        query: User query
        chunks: List of chunks with 'id' and 'text' fields
        top_k: Number of top chunks to return
        provider: LLM provider (uses default if None)
        model: Specific model (uses default if None)
        with_reasoning: Include reasoning for each ranking

    Returns:
        LLMRerankResult with reranked chunks
    """
    if not chunks:
        return LLMRerankResult(chunks=[], reranked=False, model_used="none")

    if len(chunks) <= 1:
        return LLMRerankResult(chunks=chunks, reranked=False, model_used="none")

    try:
        from src.llm_providers import call_llm
    except ImportError:
        logger.warning("LLM providers not available for reranking")
        return LLMRerankResult(chunks=chunks[:top_k], reranked=False, model_used="fallback")

    # Build passages text
    passages_text = ""
    chunk_map = {}
    for i, chunk in enumerate(chunks[:20]):  # Limit to 20 for context window
        chunk_id = chunk.get("id", f"chunk_{i}")
        chunk_text = chunk.get("text", "")[:500]  # Truncate long chunks
        passages_text += f"[{chunk_id}]: {chunk_text}\n\n"
        chunk_map[chunk_id] = chunk

    # Choose prompt
    if with_reasoning:
        prompt = RERANK_WITH_REASONING_PROMPT.format(query=query, passages=passages_text)
    else:
        prompt = RERANK_PROMPT.format(query=query, passages=passages_text)

    try:
        result = call_llm(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=0.0,
            max_tokens=500
        )

        response_text = result.get("text", "")
        model_used = result.get("meta", {}).get("model", "unknown")

        # Parse ranking
        ranked_ids = _parse_ranking(response_text)
        reasoning = None

        if with_reasoning:
            reasoning = _extract_reasoning(response_text)

        # Build reranked chunks
        reranked = []
        seen = set()

        for rank, chunk_id in enumerate(ranked_ids):
            if chunk_id in chunk_map and chunk_id not in seen:
                chunk = chunk_map[chunk_id].copy()
                chunk["llm_rank"] = rank + 1
                chunk["original_score"] = chunk.get("score", 0)
                # Adjust score based on LLM ranking
                chunk["score"] = 1.0 - (rank * 0.1)
                reranked.append(chunk)
                seen.add(chunk_id)

        # Add any chunks not in LLM ranking (preserving original order)
        for chunk in chunks:
            chunk_id = chunk.get("id")
            if chunk_id and chunk_id not in seen:
                reranked.append(chunk)
                seen.add(chunk_id)

        return LLMRerankResult(
            chunks=reranked[:top_k],
            reranked=True,
            model_used=model_used,
            reasoning=reasoning
        )

    except Exception as e:
        logger.error(f"LLM reranking failed: {e}")
        return LLMRerankResult(
            chunks=chunks[:top_k],
            reranked=False,
            model_used="error"
        )


def _parse_ranking(response: str) -> List[str]:
    """Extract ranked IDs from LLM response."""
    # Try to find JSON array
    json_match = re.search(r'\[([^\]]+)\]', response)
    if json_match:
        try:
            import json
            ids = json.loads(f"[{json_match.group(1)}]")
            return [str(id).strip() for id in ids]
        except:
            pass

    # Try RANKING: format
    ranking_match = re.search(r'RANKING:\s*\[([^\]]+)\]', response, re.IGNORECASE)
    if ranking_match:
        try:
            import json
            ids = json.loads(f"[{ranking_match.group(1)}]")
            return [str(id).strip() for id in ids]
        except:
            pass

    # Fallback: extract quoted strings
    quoted = re.findall(r'"([^"]+)"', response)
    return quoted


def _extract_reasoning(response: str) -> Optional[str]:
    """Extract reasoning section from response."""
    reasoning_match = re.search(r'REASONING:(.*?)(?:RANKING:|$)', response, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        return reasoning_match.group(1).strip()
    return None


def hybrid_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    use_cross_encoder: bool = True,
    use_llm: bool = False,
    llm_weight: float = 0.3
) -> LLMRerankResult:
    """
    Hybrid reranking combining cross-encoder and LLM scores.

    Args:
        query: User query
        chunks: Chunks to rerank
        top_k: Number to return
        use_cross_encoder: Use cross-encoder first
        use_llm: Use LLM reranking
        llm_weight: Weight for LLM scores (0-1)

    Returns:
        Combined reranking result
    """
    if not chunks:
        return LLMRerankResult(chunks=[], reranked=False, model_used="none")

    reranked_chunks = chunks.copy()
    models_used = []

    # Cross-encoder reranking
    if use_cross_encoder:
        try:
            from src.retrieval.reranker import rerank_chunks
            ce_result = rerank_chunks(query, reranked_chunks, top_k=len(reranked_chunks))
            reranked_chunks = ce_result.chunks
            models_used.append(f"cross-encoder:{ce_result.model_used}")
        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed: {e}")

    # LLM reranking
    if use_llm:
        llm_result = llm_rerank(query, reranked_chunks, top_k=len(reranked_chunks))
        if llm_result.reranked:
            models_used.append(f"llm:{llm_result.model_used}")

            # Combine scores
            llm_scores = {c.get("id"): c.get("score", 0) for c in llm_result.chunks}
            for chunk in reranked_chunks:
                chunk_id = chunk.get("id")
                if chunk_id in llm_scores:
                    original_score = chunk.get("score", 0)
                    llm_score = llm_scores[chunk_id]
                    chunk["score"] = (1 - llm_weight) * original_score + llm_weight * llm_score

            # Re-sort by combined score
            reranked_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)

    return LLMRerankResult(
        chunks=reranked_chunks[:top_k],
        reranked=bool(models_used),
        model_used="+".join(models_used) if models_used else "none"
    )
