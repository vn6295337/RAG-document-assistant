# src/orchestrator.py
from typing import List, Dict, Any, Optional, Literal
import re
import src.config as cfg
from src.ingestion.embeddings import get_embedding  # provider-agnostic embedding fn used for ingestion
from src.retrieval.retriever import query_pinecone as pinecone_search, deterministic_embedding
from src.retrieval.hybrid import hybrid_search, HybridSearchResult
from src.retrieval.reranker import rerank_chunks, RerankResult
from src.prompts.rag_prompt import build_rag_prompt
from src.query.rewriter import rewrite_query, QueryRewriteResult
from src.context.shaper import shape_context, ContextShapeResult
from src.reasoning.analyzer import analyze_query, QueryAnalysis
from src.reasoning.chain import reason_over_evidence, ReasoningResult
from src.evaluation.tracer import PipelineTracer, format_trace_summary

# -------------------------
# Citation snippet enrichment
# -------------------------
import json
from pathlib import Path as _Path

def _enrich_citations_with_snippets(result: dict, chunk_map: dict):
    """
    Mutates `result` in-place: for each citation where snippet is empty,
    set snippet to chunk_map[citation.id] if available.
    """
    if not isinstance(result, dict):
        return result
    for c in result.get("citations", []) + result.get("sources", []):
        if not isinstance(c, dict):
            continue
        if not c.get("snippet"):
            s = chunk_map.get(c.get("id"), "")
            if s:
                c["snippet"] = s
    return result

def _load_chunks_map(path: str = "data/chunks.jsonl") -> dict:
    """
    Load chunks map from JSONL file for citation enrichment.
    
    Args:
        path: Path to JSONL file containing chunk data
        
    Returns:
        Dictionary mapping chunk IDs to text content
    """
    m = {}
    pth = _Path(path)
    if not pth.exists():
        return m
        
    try:
        with pth.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed JSON lines
                    continue
                    
                cid = obj.get("id") or obj.get("chunk_id") or None
                if not cid and "filename" in obj and "chunk_id" in obj:
                    cid = f"{obj['filename']}::{obj['chunk_id']}"
                text = obj.get("text") or obj.get("chunk") or obj.get("content") or ""
                if cid:
                    m[str(cid)] = text
    except Exception as e:
        # Don't fail if chunks file can't be loaded
        pass
        
    return m

_CHUNKS_MAP = _load_chunks_map()
_CURRENT_CHUNKS_PATH = "data/chunks.jsonl"


def set_chunks_path(path: str) -> int:
    """
    Set the chunks path and reload the chunks map.

    Args:
        path: Path to the chunks JSONL file

    Returns:
        Number of chunks loaded
    """
    global _CHUNKS_MAP, _CURRENT_CHUNKS_PATH
    _CURRENT_CHUNKS_PATH = path
    _CHUNKS_MAP = _load_chunks_map(path)
    return len(_CHUNKS_MAP)


def get_current_chunks_path() -> str:
    """Get the current chunks path."""
    return _CURRENT_CHUNKS_PATH


def get_chunks_count() -> int:
    """Get the number of chunks currently loaded."""
    return len(_CHUNKS_MAP)



import json
from pathlib import Path as _Path




# Try to import a provider wrapper; if missing, use a local deterministic fallback for offline tests.
try:
    from src.llm_providers import call_llm  # thin wrapper that chooses Gemini/Groq/OpenRouter per config
except Exception:
    def call_llm(prompt: str, temperature: float = 0.0, max_tokens: int = 512, **kwargs):
        """
        Simple deterministic offline responder: return prompt summary-like text and meta.
        
        Args:
            prompt: Prompt text
            temperature: Sampling temperature (ignored in fallback)
            max_tokens: Maximum tokens (ignored in fallback)
            **kwargs: Additional arguments (ignored in fallback)
            
        Returns:
            Dict with 'text' and 'meta' keys
        """
        # Simple deterministic offline responder: return prompt summary-like text and meta.
        summary = prompt.strip().split('\n')[-1] if prompt.strip() else "No prompt provided"
        resp_text = f"[offline-llm] Answer based on provided context: {summary}" 
        return {"text": resp_text, "meta": {"provider": "local-fallback", "temperature": temperature}}


# Legacy prompt template (replaced by src.prompts.rag_prompt)
# Kept for reference during migration
_LEGACY_PROMPT_TEMPLATE = """
You are given a user query and a set of context chunks. Use the context to answer concisely.
Provide a short answer and list the ids of chunks used as citations.

User query:
{query}

Context chunks (top {k} by score):
{context}

Answer:
"""

def _extract_cited_ids_from_llm(text: str) -> List[str]:
    """
    Extract cited chunk IDs from LLM response text.

    Supports both formats:
    - [ID:chunk_id] (new structured prompt format)
    - ID:chunk_id (legacy format)

    Args:
        text: LLM response text

    Returns:
        List of cited chunk IDs (deduplicated, preserving order)
    """
    if not text or not isinstance(text, str):
        return []

    # Match both [ID:chunk_id] and plain ID:chunk_id formats
    # The bracketed format takes precedence in new prompts
    bracketed = re.findall(r"\[ID:([A-Za-z0-9_\-:.]+)\]", text)
    plain = re.findall(r"(?<!\[)ID:([A-Za-z0-9_\-:.]+)", text)

    # Combine and deduplicate while preserving order
    seen = set()
    result = []
    for cid in bracketed + plain:
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def _merge_chunks(chunk_lists: List[List[Dict[str, Any]]], top_k: int) -> List[Dict[str, Any]]:
    """
    Merge and deduplicate chunks from multiple query results.

    Uses reciprocal rank fusion (RRF) to combine rankings from different queries.
    Chunks appearing in multiple query results get boosted scores.

    Args:
        chunk_lists: List of chunk lists from different queries
        top_k: Maximum number of chunks to return

    Returns:
        Merged and deduplicated list of chunks, sorted by combined score
    """
    # RRF constant (standard value)
    k = 60

    # Track scores by chunk ID
    chunk_scores: Dict[str, float] = {}
    chunk_data: Dict[str, Dict[str, Any]] = {}

    for chunks in chunk_lists:
        for rank, chunk in enumerate(chunks):
            chunk_id = chunk.get("id", "")
            if not chunk_id:
                continue

            # RRF score contribution
            rrf_score = 1.0 / (k + rank + 1)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf_score

            # Keep the chunk data (use first occurrence)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = chunk

    # Sort by combined RRF score
    sorted_ids = sorted(chunk_scores.keys(), key=lambda x: chunk_scores[x], reverse=True)

    # Build result with updated scores
    merged = []
    for chunk_id in sorted_ids[:top_k]:
        chunk = chunk_data[chunk_id].copy()
        chunk["rrf_score"] = chunk_scores[chunk_id]
        merged.append(chunk)

    return merged


def orchestrate_query(
    query: str,
    top_k: int = 3,
    llm_params: Dict[str, Any] = None,
    rewrite_strategy: Optional[Literal["expand", "multi", "decompose", "auto", "none"]] = "auto",
    use_hybrid: bool = True,
    use_reranking: bool = True,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    chunks_path: str = None
) -> Dict[str, Any]:
    """
    Orchestrate the full RAG query pipeline: query rewriting → hybrid retrieval → reranking → LLM generation.

    Args:
        query: User query string
        top_k: Number of top chunks to retrieve
        llm_params: Parameters for LLM call (temperature, max_tokens, etc.)
        rewrite_strategy: Query rewriting strategy
            - "expand": Rule-based synonym expansion (fast, no LLM)
            - "multi": LLM generates multiple query variants
            - "decompose": LLM breaks complex query into sub-queries
            - "auto": Automatically choose based on query complexity
            - "none": Disable query rewriting
        use_hybrid: Enable hybrid search (semantic + keyword)
        use_reranking: Enable cross-encoder reranking
        semantic_weight: Weight for semantic search in hybrid mode (0-1)
        keyword_weight: Weight for keyword search in hybrid mode (0-1)
        chunks_path: Path to chunks JSONL file (uses default if None)

    Returns:
        Dict with answer, sources, citations, retrieval info, and metadata

    Raises:
        Exception: If any step in the pipeline fails
    """
    if not query or not isinstance(query, str):
        return {"answer": "", "sources": [], "citations": [], "llm_meta": {"error": "invalid_query"}}

    if llm_params is None:
        llm_params = {"temperature": 0.0, "max_tokens": 512}

    # Use default chunks path if not specified
    if chunks_path is None:
        chunks_path = _CURRENT_CHUNKS_PATH

    # Validate top_k
    if not isinstance(top_k, int) or top_k <= 0:
        top_k = 3

    # Track retrieval metadata
    retrieval_meta = {
        "hybrid_enabled": use_hybrid,
        "reranking_enabled": use_reranking
    }

    # 1) Query rewriting
    rewrite_result: Optional[QueryRewriteResult] = None
    queries_to_search = [query]

    if rewrite_strategy and rewrite_strategy != "none":
        try:
            rewrite_result = rewrite_query(
                query=query,
                num_variants=3,
                strategy=rewrite_strategy,
                use_llm=(rewrite_strategy != "expand")
            )
            queries_to_search = rewrite_result.rewritten_queries
        except Exception:
            queries_to_search = [query]

    # 2) Retrieval: hybrid or semantic-only
    all_chunk_lists = []

    for q in queries_to_search:
        try:
            if use_hybrid:
                # Fetch more for reranking
                fetch_k = top_k * 3 if use_reranking else top_k * 2
                hybrid_result = hybrid_search(
                    query=q,
                    top_k=fetch_k,
                    semantic_weight=semantic_weight,
                    keyword_weight=keyword_weight,
                    chunks_path=chunks_path
                )
                if hybrid_result.chunks:
                    all_chunk_lists.append(hybrid_result.chunks)
                    retrieval_meta["hybrid_strategy"] = hybrid_result.strategy
                    retrieval_meta["semantic_count"] = hybrid_result.semantic_count
                    retrieval_meta["keyword_count"] = hybrid_result.keyword_count
            else:
                # Semantic-only search
                chunks = pinecone_search(q, top_k=top_k * 2 if use_reranking else top_k)
                if chunks:
                    all_chunk_lists.append(chunks)
        except Exception:
            continue

    if not all_chunk_lists:
        return {"answer": "", "sources": [], "citations": [], "llm_meta": {"error": "retrieval_failed"}}

    # 3) Merge if multiple queries were used
    if len(all_chunk_lists) == 1:
        chunks = all_chunk_lists[0]
    else:
        chunks = _merge_chunks(all_chunk_lists, top_k=top_k * 2 if use_reranking else top_k)

    if not chunks:
        return {"answer": "", "sources": [], "citations": [], "llm_meta": {"error": "no_retrieval_results"}}

    # 4) Reranking (optional)
    if use_reranking and len(chunks) > 1:
        try:
            rerank_result = rerank_chunks(query=query, chunks=chunks, top_k=top_k)
            chunks = rerank_result.chunks
            retrieval_meta["rerank_model"] = rerank_result.model_used
            retrieval_meta["reranked"] = rerank_result.reranked
        except Exception as e:
            retrieval_meta["rerank_error"] = str(e)[:100]
            chunks = chunks[:top_k]
    else:
        chunks = chunks[:top_k]

    # 5) build prompt using structured prompt template
    prompt = build_rag_prompt(query=query, chunks=chunks, k=top_k)

    # 6) call LLM via unified provider wrapper
    try:
        llm_resp = call_llm(prompt=prompt, **llm_params)
    except Exception as e:
        return {"answer": "", "sources": [], "citations": [], "llm_meta": {"error": f"llm_call_failed: {str(e)}"}}

    # 7) build sources (ensure snippet comes from chunk text or fallback to local chunks map)
    sources: List[Dict[str, Any]] = []
    for c in chunks:
        # prefer chunk text from retrieval result; fallback to local chunk map
        text_from_chunk = c.get("text") or "" if isinstance(c, dict) else ""
        if not text_from_chunk:
            text_from_chunk = _CHUNKS_MAP.get(str(c.get("id"))) or _CHUNKS_MAP.get(str(c.get("chunk_id")), "") if isinstance(c, dict) else ""
        snippet = (text_from_chunk or "")[:400]
        sources.append({
            "id": c.get("id") if isinstance(c, dict) else None,
            "score": float(c.get("score", 0.0)) if isinstance(c, dict) else 0.0,
            "snippet": snippet
        })

    # 8) Build citations: prefer explicit IDs listed by LLM, else fallback to top sources
    cited_ids = _extract_cited_ids_from_llm(llm_resp.get("text", ""))
    citations: List[Dict[str, Any]] = []
    if cited_ids:
        id_map = {s["id"]: s for s in sources if s["id"]}
        for cid in cited_ids:
            if cid in id_map:
                citations.append(id_map[cid])
    if not citations:
        citations = sources

    # 9) assemble result dict, then enrich citation snippets in-place (best-effort)
    result = {
        "answer": llm_resp.get("text", "").strip() if isinstance(llm_resp, dict) else "",
        "sources": sources,
        "citations": citations,
        "llm_meta": llm_resp.get("meta", {}) if isinstance(llm_resp, dict) else {},
        "query_rewrite": {
            "original": query,
            "rewritten": queries_to_search,
            "strategy": rewrite_result.strategy_used if rewrite_result else "none"
        } if rewrite_result else None,
        "retrieval_meta": retrieval_meta
    }

    # Best-effort: enrich any empty snippets from the canonical _CHUNKS_MAP
    try:
        _enrich_citations_with_snippets(result, _CHUNKS_MAP)
    except Exception:
        # don't fail the whole call if enrichment breaks
        pass

    return result


def orchestrate_advanced(
    query: str,
    top_k: int = 5,
    llm_params: Dict[str, Any] = None,
    token_budget: int = 3000,
    enable_reasoning: bool = True,
    enable_tracing: bool = True,
    chunks_path: str = None
) -> Dict[str, Any]:
    """
    Advanced RAG orchestration with full context engineering pipeline.

    Pipeline:
    1. Query Analysis - Classify and decompose query
    2. Query Rewriting - Expand/reformulate for better retrieval
    3. Hybrid Retrieval - Semantic + keyword search
    4. Reranking - Cross-encoder precision boost
    5. Context Shaping - Dedup, prune, budget
    6. Reasoning - Chain-of-thought synthesis
    7. Generation - Produce final answer

    Args:
        query: User query
        top_k: Number of chunks to retrieve
        llm_params: LLM parameters
        token_budget: Max tokens for context
        enable_reasoning: Use reasoning-aware generation
        enable_tracing: Capture pipeline trace
        chunks_path: Path to chunks JSONL file (uses default if None)

    Returns:
        Dict with answer, sources, reasoning, trace, and metadata
    """
    if llm_params is None:
        llm_params = {"temperature": 0.0, "max_tokens": 800}

    # Use default chunks path if not specified
    if chunks_path is None:
        chunks_path = _CURRENT_CHUNKS_PATH

    # Initialize tracer
    tracer = PipelineTracer(query) if enable_tracing else None

    try:
        # 1. Query Analysis
        if tracer:
            with tracer.trace_stage("query_analysis") as stage:
                analysis = analyze_query(query, use_llm=False)
                stage.metadata = {
                    "query_type": analysis.query_type,
                    "sub_queries": len(analysis.sub_queries),
                    "reasoning_required": analysis.reasoning_required
                }
        else:
            analysis = analyze_query(query, use_llm=False)

        # 2. Query Rewriting
        if tracer:
            with tracer.trace_stage("query_rewrite") as stage:
                rewrite_result = rewrite_query(
                    query=query,
                    strategy="auto",
                    use_llm=True
                )
                stage.metadata = {
                    "strategy": rewrite_result.strategy_used,
                    "variants": len(rewrite_result.rewritten_queries)
                }
        else:
            rewrite_result = rewrite_query(query, strategy="auto", use_llm=True)

        queries_to_search = rewrite_result.rewritten_queries

        # 3. Hybrid Retrieval
        all_chunks = []
        if tracer:
            with tracer.trace_stage("retrieval") as stage:
                for q in queries_to_search:
                    result = hybrid_search(q, top_k=top_k * 2, chunks_path=chunks_path)
                    all_chunks.extend(result.chunks)
                stage.metadata = {
                    "queries_searched": len(queries_to_search),
                    "chunks_found": len(all_chunks)
                }
        else:
            for q in queries_to_search:
                result = hybrid_search(q, top_k=top_k * 2, chunks_path=chunks_path)
                all_chunks.extend(result.chunks)

        if not all_chunks:
            return {"answer": "", "error": "No chunks retrieved"}

        # Deduplicate across queries
        seen_ids = set()
        unique_chunks = []
        for c in all_chunks:
            cid = c.get("id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                unique_chunks.append(c)

        # 4. Reranking
        if tracer:
            with tracer.trace_stage("reranking") as stage:
                rerank_result = rerank_chunks(query, unique_chunks, top_k=top_k * 2)
                stage.metadata = {
                    "input_chunks": len(unique_chunks),
                    "output_chunks": len(rerank_result.chunks),
                    "model": rerank_result.model_used
                }
        else:
            rerank_result = rerank_chunks(query, unique_chunks, top_k=top_k * 2)

        chunks = rerank_result.chunks

        # 5. Context Shaping
        if tracer:
            with tracer.trace_stage("context_shaping") as stage:
                shape_result = shape_context(
                    chunks=chunks,
                    query=query,
                    token_budget=token_budget,
                    enable_pruning=True,
                    enable_compression=True
                )
                stage.metadata = {
                    "original_tokens": shape_result.original_tokens,
                    "final_tokens": shape_result.final_tokens,
                    "chunks_removed": shape_result.chunks_removed,
                    "compression": shape_result.compression_applied
                }
        else:
            shape_result = shape_context(
                chunks=chunks,
                query=query,
                token_budget=token_budget
            )

        shaped_chunks = shape_result.chunks[:top_k]

        # 6. Reasoning or Standard Generation
        if enable_reasoning and analysis.reasoning_required:
            if tracer:
                with tracer.trace_stage("reasoning") as stage:
                    reasoning_result = reason_over_evidence(
                        query=query,
                        chunks=shaped_chunks,
                        query_type=analysis.query_type
                    )
                    stage.metadata = {
                        "reasoning_type": reasoning_result.reasoning_type,
                        "evidence_used": len(reasoning_result.evidence_used),
                        "confidence": reasoning_result.confidence
                    }
            else:
                reasoning_result = reason_over_evidence(
                    query=query,
                    chunks=shaped_chunks,
                    query_type=analysis.query_type
                )

            answer = reasoning_result.answer
            reasoning_info = {
                "steps": reasoning_result.reasoning_steps,
                "evidence_used": reasoning_result.evidence_used,
                "confidence": reasoning_result.confidence,
                "type": reasoning_result.reasoning_type
            }
        else:
            # Standard generation
            if tracer:
                with tracer.trace_stage("generation") as stage:
                    prompt = build_rag_prompt(query, shaped_chunks, k=top_k)
                    llm_resp = call_llm(prompt=prompt, **llm_params)
                    answer = llm_resp.get("text", "").strip()
                    stage.metadata = {
                        "prompt_length": len(prompt),
                        "answer_length": len(answer)
                    }
            else:
                prompt = build_rag_prompt(query, shaped_chunks, k=top_k)
                llm_resp = call_llm(prompt=prompt, **llm_params)
                answer = llm_resp.get("text", "").strip()

            reasoning_info = None

        # Build sources
        sources = []
        for c in shaped_chunks:
            sources.append({
                "id": c.get("id"),
                "score": c.get("score", 0),
                "snippet": c.get("text", "")[:300]
            })

        # Build result
        result = {
            "answer": answer,
            "sources": sources,
            "query_analysis": {
                "type": analysis.query_type,
                "sub_queries": analysis.sub_queries,
                "reasoning_required": analysis.reasoning_required
            },
            "context_shaping": {
                "original_tokens": shape_result.original_tokens,
                "final_tokens": shape_result.final_tokens,
                "compression_applied": shape_result.compression_applied
            }
        }

        if reasoning_info:
            result["reasoning"] = reasoning_info

        if tracer:
            tracer.set_answer(answer)
            result["trace"] = tracer.to_dict()

        return result

    except Exception as e:
        if tracer:
            tracer.set_error(str(e))
            return {
                "answer": "",
                "error": str(e),
                "trace": tracer.to_dict()
            }
        raise