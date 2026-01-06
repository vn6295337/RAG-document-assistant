"""
Query rewriting module for improved retrieval.

Transforms user queries before retrieval to improve recall by:
- Expanding queries with synonyms and related terms
- Reformulating queries to match document terminology
- Generating multiple query variants for broader coverage
- Decomposing complex queries into sub-queries
"""

from dataclasses import dataclass
from typing import List, Optional, Literal
import re

# Try to import LLM provider for advanced rewriting
try:
    from src.llm_providers import call_llm
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class QueryRewriteResult:
    """Result of query rewriting operation."""
    original_query: str
    rewritten_queries: List[str]
    strategy_used: str


# Common synonym mappings for rule-based expansion
SYNONYMS = {
    "fix": ["resolve", "troubleshoot", "repair", "solve"],
    "error": ["issue", "problem", "failure", "bug"],
    "login": ["sign-in", "authentication", "log in"],
    "cost": ["price", "pricing", "fee", "rate"],
    "fast": ["quick", "performance", "speed", "efficient"],
    "slow": ["performance", "latency", "delay"],
    "setup": ["install", "configure", "initialization"],
    "delete": ["remove", "uninstall", "clear"],
    "create": ["add", "new", "generate", "make"],
    "update": ["modify", "change", "edit", "upgrade"],
    "get": ["retrieve", "fetch", "obtain", "access"],
    "show": ["display", "view", "list"],
}

# Prompt for LLM-based query rewriting
MULTI_QUERY_PROMPT = """You are a query rewriting assistant for a document search system.

Given a user query, generate {num_variants} alternative search queries that would help find relevant documents.

Rules:
- Each variant should use different terminology while preserving the intent
- Include both formal/technical and casual phrasings
- If the query contains multiple questions, create separate queries for each
- Output ONLY the queries, one per line, no numbering or explanations

User query: {query}

Alternative queries:"""

DECOMPOSE_PROMPT = """You are a query analysis assistant.

Given a complex user query, break it down into simple, atomic sub-queries that can be searched independently.

Rules:
- Each sub-query should focus on one specific piece of information
- Preserve the key terms from the original query
- Output ONLY the sub-queries, one per line, no numbering or explanations
- Generate between 2-4 sub-queries

User query: {query}

Sub-queries:"""


def _expand_with_synonyms(query: str) -> List[str]:
    """
    Expand query with synonyms using rule-based matching.

    Args:
        query: Original user query

    Returns:
        List containing original query plus expanded version
    """
    words = query.lower().split()
    expansions = []

    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in SYNONYMS:
            expansions.extend(SYNONYMS[clean_word])

    if expansions:
        expanded = f"{query} {' '.join(expansions)}"
        return [query, expanded]

    return [query]


def _is_complex_query(query: str) -> bool:
    """
    Determine if a query is complex enough to warrant decomposition.

    Complex queries typically:
    - Contain multiple questions (and, also, as well as)
    - Have comparison words (vs, compare, difference, between)
    - Are longer than 15 words
    """
    query_lower = query.lower()

    # Check for conjunctions suggesting multiple intents
    multi_intent_markers = [" and ", " also ", " as well as ", " plus "]
    if any(marker in query_lower for marker in multi_intent_markers):
        return True

    # Check for comparison queries
    comparison_markers = [" vs ", " versus ", "compare", "difference", "between"]
    if any(marker in query_lower for marker in comparison_markers):
        return True

    # Long queries are often complex
    if len(query.split()) > 15:
        return True

    return False


def _rewrite_with_llm(
    query: str,
    num_variants: int = 3,
    strategy: Literal["multi", "decompose"] = "multi"
) -> List[str]:
    """
    Use LLM to generate query variants.

    Args:
        query: Original user query
        num_variants: Number of variants to generate
        strategy: "multi" for multi-query, "decompose" for decomposition

    Returns:
        List of rewritten queries
    """
    if not LLM_AVAILABLE:
        return [query]

    if strategy == "decompose":
        prompt = DECOMPOSE_PROMPT.format(query=query)
    else:
        prompt = MULTI_QUERY_PROMPT.format(query=query, num_variants=num_variants)

    try:
        response = call_llm(prompt=prompt, temperature=0.3, max_tokens=256)
        text = response.get("text", "")

        # Parse response into individual queries
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

        # Filter out empty lines and numbering artifacts
        queries = []
        for line in lines:
            # Remove common numbering patterns
            cleaned = re.sub(r'^[\d\-\.\)\*]+\s*', '', line).strip()
            if cleaned and len(cleaned) > 3:
                queries.append(cleaned)

        # Always include original query
        if query not in queries:
            queries.insert(0, query)

        return queries[:num_variants + 1]

    except Exception:
        # Fallback to original query on any error
        return [query]


def rewrite_query(
    query: str,
    num_variants: int = 3,
    strategy: Optional[Literal["expand", "multi", "decompose", "auto"]] = "auto",
    use_llm: bool = True
) -> QueryRewriteResult:
    """
    Rewrite a user query to improve retrieval recall.

    Args:
        query: Original user query
        num_variants: Number of query variants to generate
        strategy: Rewriting strategy
            - "expand": Rule-based synonym expansion (fast, no LLM)
            - "multi": LLM generates multiple query variants
            - "decompose": LLM breaks complex query into sub-queries
            - "auto": Automatically choose based on query complexity
        use_llm: Whether to allow LLM-based rewriting

    Returns:
        QueryRewriteResult with original query, rewritten queries, and strategy used
    """
    query = query.strip()

    if not query:
        return QueryRewriteResult(
            original_query=query,
            rewritten_queries=[query],
            strategy_used="none"
        )

    # Auto-select strategy based on query characteristics
    if strategy == "auto":
        if _is_complex_query(query) and use_llm and LLM_AVAILABLE:
            strategy = "decompose"
        elif use_llm and LLM_AVAILABLE:
            strategy = "multi"
        else:
            strategy = "expand"

    # Execute the selected strategy
    if strategy == "expand":
        rewritten = _expand_with_synonyms(query)

    elif strategy == "multi" and use_llm and LLM_AVAILABLE:
        rewritten = _rewrite_with_llm(query, num_variants, strategy="multi")

    elif strategy == "decompose" and use_llm and LLM_AVAILABLE:
        rewritten = _rewrite_with_llm(query, num_variants, strategy="decompose")

    else:
        # Fallback to expansion if LLM not available
        rewritten = _expand_with_synonyms(query)
        strategy = "expand"

    return QueryRewriteResult(
        original_query=query,
        rewritten_queries=rewritten,
        strategy_used=strategy
    )
