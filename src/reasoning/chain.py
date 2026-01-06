"""
Chain-of-thought reasoning for RAG synthesis.

Performs explicit reasoning over retrieved evidence.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ReasoningResult:
    """Result of reasoning over evidence."""
    answer: str
    reasoning_steps: List[str]
    evidence_used: List[str]
    confidence: float
    reasoning_type: str


# Prompts for different reasoning types
SYNTHESIS_PROMPT = """Based on the evidence below, answer the query.
Show your reasoning step by step, then provide the final answer.

Query: {query}

Evidence:
{evidence}

First, analyze each piece of evidence and its relevance.
Then, synthesize the information to form a complete answer.
Finally, provide your answer with citations [ID:chunk_id].

Reasoning and Answer:"""

COMPARATIVE_PROMPT = """Compare the following based on the evidence provided.

Query: {query}

Evidence:
{evidence}

Structure your response as:
1. Key aspects of the first subject
2. Key aspects of the second subject
3. Similarities
4. Differences
5. Conclusion

Include citations [ID:chunk_id] for each claim.

Comparison:"""

ANALYTICAL_PROMPT = """Analyze and explain based on the evidence provided.

Query: {query}

Evidence:
{evidence}

Structure your response as:
1. Identify the main factors/causes
2. Explain the relationships between them
3. Draw conclusions
4. Note any limitations in the available evidence

Include citations [ID:chunk_id] for each claim.

Analysis:"""


def _format_evidence(chunks: List[Dict[str, Any]]) -> str:
    """Format chunks as numbered evidence."""
    evidence_parts = []
    for i, chunk in enumerate(chunks, 1):
        chunk_id = chunk.get("id", f"chunk_{i}")
        text = chunk.get("text", "")[:800]  # Limit length
        evidence_parts.append(f"[{chunk_id}]\n{text}")
    return "\n\n".join(evidence_parts)


def _extract_reasoning_steps(text: str) -> List[str]:
    """Extract reasoning steps from LLM response."""
    steps = []

    # Look for numbered steps
    import re
    numbered = re.findall(r'\d+\.\s*([^\n]+)', text)
    if numbered:
        steps.extend(numbered)

    # Look for bullet points
    bullets = re.findall(r'[-•]\s*([^\n]+)', text)
    if bullets:
        steps.extend(bullets)

    # If no structure found, split by sentences
    if not steps:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        steps = [s.strip() for s in sentences[:5] if len(s) > 20]

    return steps


def _extract_evidence_ids(text: str) -> List[str]:
    """Extract cited evidence IDs from response."""
    import re
    # Match [ID:...] or ID:...
    ids = re.findall(r'\[?ID:([A-Za-z0-9_\-:.]+)\]?', text)
    return list(set(ids))


def reason_over_evidence(
    query: str,
    chunks: List[Dict[str, Any]],
    query_type: str = "factual",
    use_chain_of_thought: bool = True
) -> ReasoningResult:
    """
    Apply reasoning over retrieved evidence.

    Args:
        query: User query
        chunks: Retrieved and shaped chunks
        query_type: Type of query for prompt selection
        use_chain_of_thought: Whether to request explicit reasoning

    Returns:
        ReasoningResult with answer and reasoning chain
    """
    if not chunks:
        return ReasoningResult(
            answer="I don't have enough information to answer this question.",
            reasoning_steps=["No relevant evidence found"],
            evidence_used=[],
            confidence=0.0,
            reasoning_type="no_evidence"
        )

    try:
        from src.llm_providers import call_llm
    except ImportError:
        return ReasoningResult(
            answer="LLM not available for reasoning.",
            reasoning_steps=[],
            evidence_used=[],
            confidence=0.0,
            reasoning_type="error"
        )

    # Format evidence
    evidence = _format_evidence(chunks)

    # Select prompt based on query type
    if query_type == "comparative":
        prompt = COMPARATIVE_PROMPT.format(query=query, evidence=evidence)
        reasoning_type = "comparative"
    elif query_type == "analytical":
        prompt = ANALYTICAL_PROMPT.format(query=query, evidence=evidence)
        reasoning_type = "analytical"
    else:
        prompt = SYNTHESIS_PROMPT.format(query=query, evidence=evidence)
        reasoning_type = "synthesis"

    try:
        response = call_llm(prompt=prompt, temperature=0.0, max_tokens=800)
        text = response.get("text", "").strip()

        # Extract components
        reasoning_steps = _extract_reasoning_steps(text)
        evidence_ids = _extract_evidence_ids(text)

        # Estimate confidence based on evidence usage
        confidence = min(0.9, 0.3 + 0.1 * len(evidence_ids))

        return ReasoningResult(
            answer=text,
            reasoning_steps=reasoning_steps,
            evidence_used=evidence_ids,
            confidence=confidence,
            reasoning_type=reasoning_type
        )

    except Exception as e:
        return ReasoningResult(
            answer=f"Error during reasoning: {str(e)[:100]}",
            reasoning_steps=[],
            evidence_used=[],
            confidence=0.0,
            reasoning_type="error"
        )


def iterative_retrieve_and_reason(
    query: str,
    initial_chunks: List[Dict[str, Any]],
    retrieve_fn,
    max_iterations: int = 2
) -> ReasoningResult:
    """
    Iteratively retrieve more evidence based on reasoning.

    Args:
        query: Original query
        initial_chunks: First retrieval results
        retrieve_fn: Function to retrieve more chunks (takes query, returns chunks)
        max_iterations: Maximum retrieval iterations

    Returns:
        ReasoningResult after iterative refinement
    """
    all_chunks = list(initial_chunks)
    chunk_ids = {c.get("id") for c in all_chunks}

    try:
        from src.llm_providers import call_llm
    except ImportError:
        return reason_over_evidence(query, all_chunks)

    for i in range(max_iterations):
        # Check if we need more information
        evidence = _format_evidence(all_chunks)

        check_prompt = f"""Given this query and evidence, do we need more information?
If yes, suggest a follow-up search query. If no, respond with "SUFFICIENT".

Query: {query}

Current evidence:
{evidence[:2000]}

Response (either "SUFFICIENT" or a follow-up search query):"""

        response = call_llm(prompt=check_prompt, temperature=0.0, max_tokens=100)
        text = response.get("text", "").strip()

        if "SUFFICIENT" in text.upper():
            break

        # Retrieve more based on suggested query
        follow_up = text.replace("Follow-up query:", "").strip()
        if follow_up and len(follow_up) > 5:
            try:
                new_chunks = retrieve_fn(follow_up)
                for chunk in new_chunks:
                    if chunk.get("id") not in chunk_ids:
                        all_chunks.append(chunk)
                        chunk_ids.add(chunk.get("id"))
            except Exception:
                break

    return reason_over_evidence(query, all_chunks)
