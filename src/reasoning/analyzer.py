"""
Query analysis for reasoning-aware RAG.

Classifies queries and determines retrieval strategy.
"""

from dataclasses import dataclass
from typing import List, Optional, Literal
import re


@dataclass
class QueryAnalysis:
    """Result of query analysis."""
    query_type: Literal["factual", "comparative", "procedural", "analytical", "aggregative"]
    sub_queries: List[str]
    retrieval_strategy: Literal["single", "multi", "iterative"]
    reasoning_required: bool
    confidence: float


# Patterns for query classification
COMPARATIVE_PATTERNS = [
    r'\bcompare\b', r'\bvs\.?\b', r'\bversus\b', r'\bdifference\b',
    r'\bbetter\b', r'\bworse\b', r'\bsimilar\b', r'\bunlike\b'
]

PROCEDURAL_PATTERNS = [
    r'\bhow to\b', r'\bhow do\b', r'\bhow can\b', r'\bsteps to\b',
    r'\bprocess\b', r'\bprocedure\b', r'\bmethod\b'
]

ANALYTICAL_PATTERNS = [
    r'\bwhy\b', r'\bcause\b', r'\breason\b', r'\bexplain\b',
    r'\banalyz\b', r'\bimpact\b', r'\beffect\b', r'\bimplication\b'
]

AGGREGATIVE_PATTERNS = [
    r'\blist\b', r'\ball\b', r'\bevery\b', r'\benumerate\b',
    r'\bsummarize\b', r'\boverview\b', r'\bmain\b'
]


def _classify_query(query: str) -> tuple[str, float]:
    """
    Classify query type based on patterns.

    Returns:
        Tuple of (query_type, confidence)
    """
    query_lower = query.lower()

    # Check each pattern type
    for pattern in COMPARATIVE_PATTERNS:
        if re.search(pattern, query_lower):
            return "comparative", 0.8

    for pattern in PROCEDURAL_PATTERNS:
        if re.search(pattern, query_lower):
            return "procedural", 0.8

    for pattern in ANALYTICAL_PATTERNS:
        if re.search(pattern, query_lower):
            return "analytical", 0.8

    for pattern in AGGREGATIVE_PATTERNS:
        if re.search(pattern, query_lower):
            return "aggregative", 0.8

    # Default to factual
    return "factual", 0.6


def _decompose_query(query: str, query_type: str) -> List[str]:
    """
    Decompose query into sub-queries based on type.

    Args:
        query: Original query
        query_type: Classified query type

    Returns:
        List of sub-queries
    """
    sub_queries = [query]  # Always include original

    if query_type == "comparative":
        # Try to extract comparison subjects
        # Pattern: "compare X and Y" or "X vs Y"
        vs_match = re.search(r'(.+?)\s+(?:vs\.?|versus|and|compared to)\s+(.+)', query, re.IGNORECASE)
        if vs_match:
            subject1 = vs_match.group(1).strip()
            subject2 = vs_match.group(2).strip()
            # Remove "compare" from subject1 if present
            subject1 = re.sub(r'^compare\s+', '', subject1, flags=re.IGNORECASE)
            sub_queries.extend([
                f"{subject1}",
                f"{subject2}"
            ])

    elif query_type == "analytical":
        # Extract the subject being analyzed
        why_match = re.search(r'why\s+(?:does|is|do|are|did|was|were)?\s*(.+)', query, re.IGNORECASE)
        if why_match:
            subject = why_match.group(1).strip()
            sub_queries.append(f"causes of {subject}")
            sub_queries.append(f"factors affecting {subject}")

    elif query_type == "aggregative":
        # Keep as-is, but may expand later with iterative retrieval
        pass

    return sub_queries


def _determine_strategy(query_type: str, sub_queries: List[str]) -> str:
    """Determine retrieval strategy based on query analysis."""
    if query_type in ["comparative", "aggregative"]:
        return "multi"
    elif query_type == "analytical" and len(sub_queries) > 1:
        return "iterative"
    else:
        return "single"


def analyze_query(
    query: str,
    use_llm: bool = False
) -> QueryAnalysis:
    """
    Analyze query to determine type and retrieval strategy.

    Args:
        query: User query
        use_llm: Whether to use LLM for classification (more accurate but slower)

    Returns:
        QueryAnalysis with type, sub-queries, and strategy
    """
    if use_llm:
        return _analyze_with_llm(query)

    # Rule-based analysis
    query_type, confidence = _classify_query(query)
    sub_queries = _decompose_query(query, query_type)
    strategy = _determine_strategy(query_type, sub_queries)

    # Reasoning required for non-factual queries
    reasoning_required = query_type in ["comparative", "analytical"]

    return QueryAnalysis(
        query_type=query_type,
        sub_queries=sub_queries,
        retrieval_strategy=strategy,
        reasoning_required=reasoning_required,
        confidence=confidence
    )


def _analyze_with_llm(query: str) -> QueryAnalysis:
    """
    Analyze query using LLM for better accuracy.
    """
    try:
        from src.llm_providers import call_llm

        prompt = f"""Analyze this query and respond with exactly 3 lines:
Line 1: Query type (one of: factual, comparative, procedural, analytical, aggregative)
Line 2: Sub-queries (comma-separated list of 1-3 sub-queries to search)
Line 3: Reasoning needed (yes or no)

Query: {query}

Analysis:"""

        response = call_llm(prompt=prompt, temperature=0.0, max_tokens=150)
        text = response.get("text", "").strip()
        lines = text.split("\n")

        if len(lines) >= 3:
            query_type = lines[0].strip().lower()
            if query_type not in ["factual", "comparative", "procedural", "analytical", "aggregative"]:
                query_type = "factual"

            sub_queries = [q.strip() for q in lines[1].split(",") if q.strip()]
            if not sub_queries:
                sub_queries = [query]

            reasoning = "yes" in lines[2].lower()

            strategy = "multi" if len(sub_queries) > 1 else "single"

            return QueryAnalysis(
                query_type=query_type,
                sub_queries=sub_queries,
                retrieval_strategy=strategy,
                reasoning_required=reasoning,
                confidence=0.9
            )

    except Exception:
        pass

    # Fallback to rule-based
    return analyze_query(query, use_llm=False)
