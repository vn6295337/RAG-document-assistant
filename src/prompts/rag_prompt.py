"""
Structured prompt templates for RAG pipeline.

This module implements a layered prompt architecture:
- SYSTEM: Role and behavior rules (fixed)
- DEVELOPER: Grounding rules and constraints (RAG-specific)
- CONTEXT: Retrieved chunks (dynamic)
- USER: Query (dynamic)
"""

from typing import List, Dict, Any

# Layer 1: System prompt - defines the assistant's role and core behavior
SYSTEM_PROMPT = """You are a document assistant. You answer questions using ONLY the provided context.
You are precise, concise, and always cite your sources."""

# Layer 2: Developer prompt - RAG-specific grounding rules and output format
DEVELOPER_PROMPT = """## Grounding Rules
- Answer ONLY using information from the CONTEXT section below
- If the context doesn't contain enough information to answer, say "I don't have enough information to answer this based on the provided documents"
- NEVER fabricate or infer information not explicitly present in the context
- Keep answers under 3 paragraphs unless the query explicitly asks for detail

## Citation Format
- Cite sources inline using [ID:chunk_id] format immediately after the relevant claim
- Every factual claim MUST have a citation
- At the end of your answer, list all cited chunks under "Sources:" with their IDs"""

# Layer 3: Context template - structured container for retrieved chunks
CONTEXT_TEMPLATE = """## Context Chunks
The following are relevant excerpts from the document corpus, ranked by relevance:

{chunks}"""

# Layer 4: User query template
USER_TEMPLATE = """## Question
{query}"""


def format_chunk(chunk: Dict[str, Any], index: int) -> str:
    """
    Format a single chunk with clear boundaries and metadata.

    Args:
        chunk: Dict with 'id', 'text', and optionally 'score', 'metadata' keys
        index: Chunk position (for display)

    Returns:
        Formatted chunk string
    """
    chunk_id = chunk.get("id", f"chunk_{index}")
    score = chunk.get("score")
    text = chunk.get("text", "")

    # Build score line only if score exists
    score_line = f"Relevance Score: {score:.3f}" if score is not None else ""

    formatted = f"""---
Chunk ID: {chunk_id}
{score_line}
Content:
{text}
---"""
    return formatted


def build_rag_prompt(
    query: str,
    chunks: List[Dict[str, Any]],
    k: int = 5,
    include_scores: bool = True
) -> str:
    """
    Build a structured RAG prompt from query and retrieved chunks.

    The prompt follows a clear hierarchy:
    1. SYSTEM - Role definition
    2. DEVELOPER - Grounding rules and format constraints
    3. CONTEXT - Retrieved document chunks
    4. USER - The actual query

    Args:
        query: User's question
        chunks: List of dicts with 'id', 'text', and optionally 'score' keys
        k: Maximum number of chunks to include
        include_scores: Whether to show relevance scores

    Returns:
        Formatted prompt string ready for LLM
    """
    # Format each chunk with clear boundaries
    chunk_strs = []
    for i, chunk in enumerate(chunks[:k]):
        if not include_scores:
            # Remove score for cleaner output if desired
            chunk_copy = {k: v for k, v in chunk.items() if k != "score"}
            chunk_strs.append(format_chunk(chunk_copy, i))
        else:
            chunk_strs.append(format_chunk(chunk, i))

    formatted_chunks = "\n\n".join(chunk_strs) if chunk_strs else "(No relevant context found)"

    # Assemble full prompt with clear section markers
    prompt = f"""{SYSTEM_PROMPT}

{DEVELOPER_PROMPT}

{CONTEXT_TEMPLATE.format(chunks=formatted_chunks)}

{USER_TEMPLATE.format(query=query)}

## Answer"""

    return prompt
