# src/retrieval/hyde.py
"""HyDE (Hypothetical Document Embeddings) for improved retrieval."""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HyDEResult:
    """Result of HyDE generation."""
    hypothetical_doc: str
    original_query: str
    model_used: str


HYDE_PROMPT = """Given the following question, write a short paragraph that would be a good answer to this question. Write as if you are quoting from an authoritative document. Do not include phrases like "According to" or "The document states". Just write the factual content directly.

Question: {query}

Hypothetical answer paragraph:"""


def generate_hypothetical_document(
    query: str,
    provider: str = None,
    model: str = None,
    max_tokens: int = 150
) -> HyDEResult:
    """
    Generate a hypothetical document that would answer the query.
    This is then embedded and used for similarity search.

    Uses existing LLM providers (no extra cost).
    """
    from src.llm_providers import call_llm

    prompt = HYDE_PROMPT.format(query=query)

    try:
        result = call_llm(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=0.7,  # Some creativity for hypothetical doc
            max_tokens=max_tokens
        )

        hypothetical = result.get('text', '').strip()
        model_used = result.get('meta', {}).get('model', 'unknown')

        if not hypothetical:
            logger.warning("HyDE generation returned empty result")
            return HyDEResult(
                hypothetical_doc=query,  # Fallback to original query
                original_query=query,
                model_used=model_used
            )

        return HyDEResult(
            hypothetical_doc=hypothetical,
            original_query=query,
            model_used=model_used
        )

    except Exception as e:
        logger.error(f"HyDE generation failed: {e}")
        return HyDEResult(
            hypothetical_doc=query,  # Fallback
            original_query=query,
            model_used="fallback"
        )


def hyde_search(
    query: str,
    search_fn,  # Function that takes query string and returns results
    use_hyde: bool = True,
    combine_results: bool = True,
    provider: str = None
) -> Dict[str, Any]:
    """
    Perform search with optional HyDE enhancement.

    Args:
        query: User's original query
        search_fn: Search function to call (e.g., hybrid_search)
        use_hyde: Whether to use HyDE
        combine_results: If True, combine HyDE and original query results
        provider: LLM provider for HyDE generation

    Returns:
        Search results with HyDE metadata
    """
    results = {
        'hyde_used': False,
        'hypothetical_doc': None,
        'results': []
    }

    if not use_hyde:
        results['results'] = search_fn(query)
        return results

    # Generate hypothetical document
    hyde_result = generate_hypothetical_document(query, provider=provider)
    results['hyde_used'] = True
    results['hypothetical_doc'] = hyde_result.hypothetical_doc
    results['model_used'] = hyde_result.model_used

    # Search with hypothetical document
    hyde_results = search_fn(hyde_result.hypothetical_doc)

    if combine_results:
        # Also search with original query
        original_results = search_fn(query)

        # Combine and deduplicate (prefer higher scores)
        seen_ids = set()
        combined = []

        for r in hyde_results + original_results:
            rid = r.get('id') or r.get('chunk_id')
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                combined.append(r)

        # Sort by score
        combined.sort(key=lambda x: x.get('score', 0), reverse=True)
        results['results'] = combined
    else:
        results['results'] = hyde_results

    return results
