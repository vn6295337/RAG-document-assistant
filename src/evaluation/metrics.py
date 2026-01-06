"""
Evaluation metrics for RAG pipeline.

Measures retrieval and generation quality.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re


@dataclass
class EvaluationResult:
    """Result of evaluation."""
    retrieval_score: float
    faithfulness_score: float
    completeness_score: float
    format_score: float
    overall_score: float
    issues: List[str]
    suggestions: List[str]


def evaluate_retrieval(
    query: str,
    chunks: List[Dict[str, Any]],
    expected_keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Evaluate retrieval quality.

    Args:
        query: Original query
        chunks: Retrieved chunks
        expected_keywords: Keywords expected in results

    Returns:
        Dict with retrieval metrics
    """
    if not chunks:
        return {
            "score": 0.0,
            "chunks_retrieved": 0,
            "keyword_coverage": 0.0,
            "issues": ["No chunks retrieved"]
        }

    issues = []

    # Check number of chunks
    num_chunks = len(chunks)
    if num_chunks < 2:
        issues.append("Very few chunks retrieved")

    # Check scores
    scores = [c.get("score", 0) for c in chunks]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0

    if max_score < 0.5:
        issues.append("Low relevance scores - query may not match documents")

    # Check keyword coverage
    keyword_coverage = 0.0
    if expected_keywords:
        combined_text = " ".join(c.get("text", "").lower() for c in chunks)
        matches = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
        keyword_coverage = matches / len(expected_keywords)
        if keyword_coverage < 0.5:
            issues.append(f"Only {matches}/{len(expected_keywords)} expected keywords found")

    # Calculate overall retrieval score
    score = (avg_score * 0.5) + (min(num_chunks / 5, 1.0) * 0.3) + (keyword_coverage * 0.2)

    return {
        "score": score,
        "chunks_retrieved": num_chunks,
        "avg_relevance": avg_score,
        "max_relevance": max_score,
        "keyword_coverage": keyword_coverage,
        "issues": issues
    }


def evaluate_generation(
    query: str,
    answer: str,
    chunks: List[Dict[str, Any]],
    expected_keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Evaluate generation quality.

    Args:
        query: Original query
        answer: Generated answer
        chunks: Context chunks used
        expected_keywords: Keywords expected in answer

    Returns:
        Dict with generation metrics
    """
    if not answer or answer.strip() == "":
        return {
            "score": 0.0,
            "faithfulness": 0.0,
            "completeness": 0.0,
            "format_score": 0.0,
            "issues": ["No answer generated"]
        }

    issues = []
    suggestions = []

    # Check for abstention
    abstention_phrases = [
        "don't have enough information",
        "cannot answer",
        "no information",
        "not mentioned"
    ]
    is_abstention = any(phrase in answer.lower() for phrase in abstention_phrases)

    # Check citations
    citations = re.findall(r'\[ID:([A-Za-z0-9_\-:.]+)\]', answer)
    has_citations = len(citations) > 0

    if not has_citations and not is_abstention:
        issues.append("No citations in answer")
        suggestions.append("Ensure citations are included for factual claims")

    # Check answer length
    word_count = len(answer.split())
    if word_count < 10 and not is_abstention:
        issues.append("Answer too short")
    elif word_count > 500:
        issues.append("Answer may be too long")

    # Check faithfulness (simple check: do cited chunks exist?)
    chunk_ids = {c.get("id") for c in chunks}
    invalid_citations = [c for c in citations if c not in chunk_ids]
    if invalid_citations:
        issues.append(f"Citations to non-existent chunks: {invalid_citations[:3]}")

    # Check completeness (keyword coverage)
    completeness = 1.0
    if expected_keywords:
        answer_lower = answer.lower()
        matches = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
        completeness = matches / len(expected_keywords)
        if completeness < 0.5:
            issues.append(f"Missing expected keywords in answer")

    # Calculate format score
    format_score = 0.5
    if has_citations:
        format_score += 0.3
    if "Sources:" in answer or "References:" in answer:
        format_score += 0.2

    # Calculate faithfulness (simplified)
    faithfulness = 1.0 if not invalid_citations else 0.7
    if is_abstention:
        faithfulness = 1.0  # Abstention is faithful

    # Overall score
    overall = (faithfulness * 0.4) + (completeness * 0.3) + (format_score * 0.3)

    return {
        "score": overall,
        "faithfulness": faithfulness,
        "completeness": completeness,
        "format_score": format_score,
        "citations_count": len(citations),
        "is_abstention": is_abstention,
        "word_count": word_count,
        "issues": issues,
        "suggestions": suggestions
    }


def evaluate_full(
    query: str,
    chunks: List[Dict[str, Any]],
    answer: str,
    expected_keywords: List[str] = None
) -> EvaluationResult:
    """
    Full evaluation of retrieval and generation.

    Args:
        query: Original query
        chunks: Retrieved chunks
        answer: Generated answer
        expected_keywords: Keywords expected in results

    Returns:
        EvaluationResult with all metrics
    """
    retrieval = evaluate_retrieval(query, chunks, expected_keywords)
    generation = evaluate_generation(query, answer, chunks, expected_keywords)

    all_issues = retrieval.get("issues", []) + generation.get("issues", [])
    all_suggestions = generation.get("suggestions", [])

    # Weight retrieval and generation equally
    overall = (retrieval["score"] * 0.5) + (generation["score"] * 0.5)

    return EvaluationResult(
        retrieval_score=retrieval["score"],
        faithfulness_score=generation["faithfulness"],
        completeness_score=generation["completeness"],
        format_score=generation["format_score"],
        overall_score=overall,
        issues=all_issues,
        suggestions=all_suggestions
    )


def evaluate_with_llm(
    query: str,
    answer: str,
    context: str
) -> Dict[str, Any]:
    """
    Use LLM to evaluate answer quality (more accurate but costly).

    Args:
        query: Original query
        answer: Generated answer
        context: Context provided to generator

    Returns:
        Dict with LLM-based evaluation scores
    """
    try:
        from src.llm_providers import call_llm
    except ImportError:
        return {"error": "LLM not available"}

    prompt = f"""Evaluate this RAG answer on a scale of 0-10 for each criterion.
Return scores as: faithfulness,completeness,relevance

Criteria:
- Faithfulness: Is the answer supported by the context? (0=hallucinated, 10=fully grounded)
- Completeness: Does it fully address the query? (0=misses key points, 10=comprehensive)
- Relevance: Is the answer relevant and useful? (0=off-topic, 10=directly answers)

Query: {query}

Context: {context[:1500]}

Answer: {answer}

Scores (comma-separated, e.g., "8,7,9"):"""

    try:
        response = call_llm(prompt=prompt, temperature=0.0, max_tokens=50)
        text = response.get("text", "").strip()

        # Parse scores
        scores = [float(s.strip()) / 10 for s in text.split(",")[:3]]
        if len(scores) == 3:
            return {
                "faithfulness": scores[0],
                "completeness": scores[1],
                "relevance": scores[2],
                "overall": sum(scores) / 3
            }
    except Exception as e:
        return {"error": str(e)}

    return {"error": "Failed to parse LLM evaluation"}
