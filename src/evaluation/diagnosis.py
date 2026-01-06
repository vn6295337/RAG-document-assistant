"""
Failure diagnosis for RAG pipeline.

Identifies root causes when answers are wrong or missing.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class DiagnosisResult:
    """Result of failure diagnosis."""
    root_cause: str
    stage_failed: str
    confidence: float
    details: str
    suggestions: List[str]
    alternative_queries: List[str]


def diagnose_failure(
    query: str,
    chunks: List[Dict[str, Any]],
    answer: str,
    expected_content: str = None
) -> DiagnosisResult:
    """
    Diagnose why a RAG query failed or gave poor results.

    Args:
        query: Original query
        chunks: Retrieved chunks
        answer: Generated answer
        expected_content: What the answer should contain (optional)

    Returns:
        DiagnosisResult with root cause and suggestions
    """
    suggestions = []
    alternative_queries = []

    # Case 1: No chunks retrieved
    if not chunks:
        return DiagnosisResult(
            root_cause="retrieval_failure",
            stage_failed="retrieval",
            confidence=0.9,
            details="No chunks were retrieved for this query",
            suggestions=[
                "Check if documents are indexed",
                "Try broader search terms",
                "Use keyword search for exact matches"
            ],
            alternative_queries=_generate_alternative_queries(query)
        )

    # Case 2: Low relevance scores
    scores = [c.get("score", 0) for c in chunks]
    avg_score = sum(scores) / len(scores) if scores else 0

    if avg_score < 0.4:
        return DiagnosisResult(
            root_cause="low_relevance",
            stage_failed="retrieval",
            confidence=0.8,
            details=f"Retrieved chunks have low relevance (avg score: {avg_score:.2f})",
            suggestions=[
                "Query terms may not match document vocabulary",
                "Try rephrasing the query",
                "Use query expansion or synonyms"
            ],
            alternative_queries=_generate_alternative_queries(query)
        )

    # Case 3: Abstention (model refused to answer)
    abstention_phrases = [
        "don't have enough information",
        "cannot answer",
        "no information",
        "not mentioned",
        "not enough"
    ]
    is_abstention = any(phrase in answer.lower() for phrase in abstention_phrases)

    if is_abstention:
        # Check if chunks actually contain relevant info
        combined_text = " ".join(c.get("text", "") for c in chunks)
        query_words = set(query.lower().split())
        chunk_words = set(combined_text.lower().split())
        overlap = len(query_words & chunk_words) / len(query_words) if query_words else 0

        if overlap > 0.5:
            return DiagnosisResult(
                root_cause="context_interpretation",
                stage_failed="generation",
                confidence=0.7,
                details="Chunks contain relevant terms but LLM couldn't extract answer",
                suggestions=[
                    "Context may be fragmented across chunks",
                    "Try retrieving more chunks",
                    "Consider using reasoning-aware prompts"
                ],
                alternative_queries=[]
            )
        else:
            return DiagnosisResult(
                root_cause="topic_mismatch",
                stage_failed="retrieval",
                confidence=0.8,
                details="Retrieved chunks don't appear to cover the query topic",
                suggestions=[
                    "Query topic may not be in the document corpus",
                    "Try different terminology",
                    "Check if relevant documents are indexed"
                ],
                alternative_queries=_generate_alternative_queries(query)
            )

    # Case 4: Expected content not in answer
    if expected_content:
        expected_words = set(expected_content.lower().split())
        answer_words = set(answer.lower().split())
        coverage = len(expected_words & answer_words) / len(expected_words) if expected_words else 1

        if coverage < 0.3:
            # Check if expected content is in chunks
            combined_chunks = " ".join(c.get("text", "").lower() for c in chunks)
            in_chunks = any(word in combined_chunks for word in expected_words)

            if in_chunks:
                return DiagnosisResult(
                    root_cause="generation_miss",
                    stage_failed="generation",
                    confidence=0.7,
                    details="Expected information is in chunks but not in answer",
                    suggestions=[
                        "LLM may have focused on wrong parts of context",
                        "Try more specific prompting",
                        "Increase context relevance through reranking"
                    ],
                    alternative_queries=[]
                )
            else:
                return DiagnosisResult(
                    root_cause="retrieval_miss",
                    stage_failed="retrieval",
                    confidence=0.8,
                    details="Expected information not found in retrieved chunks",
                    suggestions=[
                        "Relevant chunks may not have been retrieved",
                        "Try different query formulation",
                        "Increase top_k for more coverage"
                    ],
                    alternative_queries=_generate_alternative_queries(query)
                )

    # Case 5: Default - unclear failure
    return DiagnosisResult(
        root_cause="unknown",
        stage_failed="unknown",
        confidence=0.5,
        details="Unable to determine specific failure cause",
        suggestions=[
            "Review the query for clarity",
            "Check chunk quality manually",
            "Try with different retrieval settings"
        ],
        alternative_queries=_generate_alternative_queries(query)
    )


def _generate_alternative_queries(query: str) -> List[str]:
    """Generate alternative query formulations."""
    alternatives = []

    # Remove question words
    cleaned = query.lower()
    for word in ["what", "how", "why", "when", "where", "who", "which"]:
        cleaned = cleaned.replace(word + " ", "")
        cleaned = cleaned.replace(word + "'s ", "")

    # Extract key terms
    words = [w for w in cleaned.split() if len(w) > 3]

    if words:
        # Just key terms
        alternatives.append(" ".join(words[:5]))

        # With "about"
        if len(words) >= 2:
            alternatives.append(f"about {words[0]} {words[1]}")

    return alternatives[:3]


def run_diagnostics_suite(
    query: str,
    chunks: List[Dict[str, Any]],
    answer: str
) -> Dict[str, Any]:
    """
    Run comprehensive diagnostics on a query result.

    Returns a detailed report for debugging.
    """
    diagnosis = diagnose_failure(query, chunks, answer)

    # Additional checks
    chunk_analysis = {
        "count": len(chunks),
        "avg_length": sum(len(c.get("text", "")) for c in chunks) / len(chunks) if chunks else 0,
        "sources": list(set(c.get("id", "").split("::")[0] for c in chunks if c.get("id"))),
        "score_range": (
            min(c.get("score", 0) for c in chunks) if chunks else 0,
            max(c.get("score", 0) for c in chunks) if chunks else 0
        )
    }

    answer_analysis = {
        "length": len(answer),
        "word_count": len(answer.split()),
        "has_citations": "[ID:" in answer,
        "is_abstention": any(p in answer.lower() for p in ["don't have", "cannot answer"])
    }

    return {
        "diagnosis": {
            "root_cause": diagnosis.root_cause,
            "stage_failed": diagnosis.stage_failed,
            "confidence": diagnosis.confidence,
            "details": diagnosis.details
        },
        "suggestions": diagnosis.suggestions,
        "alternative_queries": diagnosis.alternative_queries,
        "chunk_analysis": chunk_analysis,
        "answer_analysis": answer_analysis
    }
