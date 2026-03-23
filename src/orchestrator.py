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

def _load_chunks_map(path: str = None) -> dict:
    """
    Load chunks map from JSONL file for citation enrichment.
    """
    if path is None:
        path = "data/chunks.jsonl"
        # In production, default to /tmp if the bundled one doesn't exist
        if os.getenv("ENV") == "production" and not os.path.exists(path):
            if os.path.exists("/tmp/chunks.jsonl"):
                path = "/tmp/chunks.jsonl"

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
                    continue

                cid = obj.get("id") or obj.get("chunk_id") or None
                if not cid and "filename" in obj and "chunk_id" in obj:
                    cid = f"{obj['filename']}::{obj['chunk_id']}"
                text = obj.get("text") or obj.get("chunk") or obj.get("content") or ""
                if cid:
                    m[str(cid)] = text
    except Exception as e:
        pass

    return m

import os
_CHUNKS_MAP = _load_chunks_map()
_CURRENT_CHUNKS_PATH = "data/chunks.jsonl"
if os.getenv("ENV") == "production" and not os.path.exists(_CURRENT_CHUNKS_PATH):
    if os.path.exists("/tmp/chunks.jsonl"):
        _CURRENT_CHUNKS_PATH = "/tmp/chunks.jsonl"

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


# Langfuse observability (optional - graceful fallback if not available)
try:
    from langfuse.decorators import observe, langfuse_context
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False
    # Fallback: no-op decorator and context
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    class _DummyContext:
        def update_current_trace(self, *args, **kwargs):
            pass
        def update_current_observation(self, *args, **kwargs):
            pass
    langfuse_context = _DummyContext()

async def _dummy_async():
    pass

@observe()
async def orchestrate_zero_storage(
    query: str,
    access_token: str,
    top_k: int = 3,
    use_rewriting: bool = True,
    rewrite_strategy: str = "auto",
    use_reranking: bool = True,
    use_context_shaping: bool = True,
    token_budget: int = 2000,
    use_hyde: bool = False,
    llm_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Unified Zero-Storage RAG orchestration.
    
    This function re-fetches document text from Dropbox at query time,
    ensuring no raw text is stored on the server.
    
    Features:
    - Query rewriting (LiteLLM-ready)
    - Hybrid-Cloud compatible (Offloads embeddings)
    - Zero-storage: RAM-only re-fetching
    - Context shaping & Reranking
    """
    import httpx
    from pinecone import Pinecone
    from src.ingestion.embeddings import get_embedding
    from src.llm_providers import call_llm
    
    if not query:
        return {"error": "No query provided", "answer": ""}
    
    if not access_token:
        return {"error": "Dropbox access token required for zero-storage queries", "answer": ""}
        
    if llm_params is None:
        llm_params = {"temperature": 0.0, "max_tokens": 512}

    langfuse_context.update_current_trace(
        name="Zero-Storage Query",
        input=query,
        metadata={
            "top_k": top_k,
            "use_rewriting": use_rewriting,
            "rewrite_strategy": rewrite_strategy,
            "use_hyde": use_hyde
        }
    )

    # Track pipeline metadata
    pipeline_meta = {
        "rewriting_enabled": use_rewriting,
        "rewrite_strategy_requested": rewrite_strategy,
        "reranking_enabled": use_reranking,
        "context_shaping_enabled": use_context_shaping,
        "hyde_requested": use_hyde,
        "hyde_used": False
    }

    try:
        # 1. Query rewriting (optional)
        queries_to_search = [query]
        rewrite_result: Optional[QueryRewriteResult] = None
        if use_rewriting and rewrite_strategy != "none":
            try:
                rewrite_result = rewrite_query(
                    query=query,
                    num_variants=3,
                    strategy=rewrite_strategy,
                    use_llm=(rewrite_strategy != "expand")
                )
                queries_to_search = rewrite_result.rewritten_queries[:4]
                pipeline_meta["rewrite_strategy"] = rewrite_result.strategy_used
                pipeline_meta["query_variants"] = len(queries_to_search)
                pipeline_meta["rewritten_queries"] = queries_to_search
            except Exception as e:
                pipeline_meta["rewrite_error"] = str(e)[:100]
                queries_to_search = [query]

        # 2. Search Pinecone with all query variants
        pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
        idx_meta = pc.describe_index(cfg.PINECONE_INDEX_NAME)
        host = getattr(idx_meta, "host", None) or idx_meta.get("host")
        index = pc.Index(host=host)

        # Fetch more results for reranking
        fetch_k = top_k * 3 if use_reranking else top_k

        all_matches = []
        seen_ids = set()

        for q in queries_to_search:
            search_queries = [q]
            if use_hyde:
                try:
                    from src.retrieval.hyde import generate_hypothetical_document

                    hyde_result = generate_hypothetical_document(q)
                    hypothetical = hyde_result.hypothetical_doc.strip()
                    if hypothetical and hypothetical != q:
                        search_queries.insert(0, hypothetical)
                        pipeline_meta["hyde_used"] = True
                        pipeline_meta["hyde_model"] = hyde_result.model_used
                except Exception as e:
                    pipeline_meta["hyde_error"] = str(e)[:100]

            for search_query in search_queries:
                query_embedding = get_embedding(
                    search_query, provider="sentence-transformers", dim=384
                )
                results = index.query(
                    vector=query_embedding,
                    top_k=fetch_k,
                    include_metadata=True
                )
            # Deduplicate across query variants
                for match in results.matches:
                    if match.id not in seen_ids:
                        seen_ids.add(match.id)
                        all_matches.append(match)

        if not all_matches:
            return {"answer": "No relevant documents found.", "citations": [], "pipeline_meta": pipeline_meta}

        pipeline_meta["initial_matches"] = len(all_matches)

        # 3. Group chunks by file for efficient fetching
        files_to_fetch = {}
        for match in all_matches:
            meta = match.metadata or {}
            file_path = meta.get("file_path", "")
            if file_path:
                if file_path not in files_to_fetch:
                    files_to_fetch[file_path] = []
                files_to_fetch[file_path].append({
                    "id": match.id,
                    "score": match.score,
                    "start_char": meta.get("start_char", 0),
                    "end_char": meta.get("end_char", 0),
                    "filename": meta.get("filename", ""),
                })

        # 4. Re-fetch files from Dropbox and extract chunks
        chunks_with_text = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for file_path, chunks in files_to_fetch.items():
                # Fetch file content
                response = await client.post(
                    "https://content.dropboxapi.com/2/files/download",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Dropbox-API-Arg": f'{{"path": "{file_path}"}}'
                    }
                )

                if response.status_code == 200:
                    # Use Docling (zero-disk) for consistent text extraction and offset matching
                    try:
                        from src.ingestion.docling_loader import load_document_from_bytes
                        from pathlib import Path
                        filename = Path(file_path).name
                        doc = load_document_from_bytes(response.content, filename)
                        
                        if doc.status == "OK" and doc.full_text.strip():
                            file_content = doc.full_text
                        else:
                            # Fallback for plain text or failures
                            file_content = response.text
                    except Exception as e:
                        pipeline_meta["re-fetch_parse_error"] = str(e)[:100]
                        file_content = response.text

                    # Extract each chunk using stored positions
                    for chunk in chunks:
                        start = chunk["start_char"]
                        end = chunk["end_char"]
                        chunk_text = file_content[start:end] if end > start else file_content[:500]
                        chunks_with_text.append({
                            "id": chunk["id"],
                            "score": chunk["score"],
                            "text": chunk_text.strip(),
                            "filename": chunk["filename"],
                        })

        if not chunks_with_text:
            return {"answer": "Could not retrieve document content. Please reconnect to Dropbox.", "citations": [], "pipeline_meta": pipeline_meta}

        # Sort by initial score
        chunks_with_text.sort(key=lambda x: x["score"], reverse=True)

        # 5. Reranking (optional) - now we have text, can use cross-encoder
        if use_reranking and len(chunks_with_text) > 1:
            try:
                rerank_result = rerank_chunks(
                    query=query,
                    chunks=chunks_with_text,
                    top_k=top_k * 2  # Keep more for context shaping
                )
                chunks_with_text = rerank_result.chunks
                pipeline_meta["rerank_model"] = rerank_result.model_used
                pipeline_meta["reranked"] = rerank_result.reranked
            except Exception as e:
                pipeline_meta["rerank_error"] = str(e)[:50]
                # Continue with original order

        # 6. Context shaping (optional) - token budget, dedup, pruning
        if use_context_shaping:
            try:
                shape_result = shape_context(
                    chunks=chunks_with_text,
                    query=query,
                    token_budget=token_budget,
                    enable_pruning=True,
                    enable_compression=False  # Keep original text for accuracy
                )
                chunks_with_text = shape_result.chunks[:top_k]
                pipeline_meta["original_tokens"] = shape_result.original_tokens
                pipeline_meta["final_tokens"] = shape_result.final_tokens
                pipeline_meta["chunks_removed"] = shape_result.chunks_removed
            except Exception as e:
                pipeline_meta["shaping_error"] = str(e)[:50]
                chunks_with_text = chunks_with_text[:top_k]
        else:
            chunks_with_text = chunks_with_text[:top_k]

        # 7. Build prompt and call LLM
        prompt = build_rag_prompt(query=query, chunks=chunks_with_text, k=top_k)
        llm_resp = call_llm(prompt=prompt, **llm_params)

        # 8. Build response
        citations = [
            {"id": c["id"], "score": c["score"], "snippet": c["text"][:200]}
            for c in chunks_with_text[:top_k]
        ]

        return {
            "answer": llm_resp.get("text", "").strip(),
            "citations": citations,
            "pipeline_meta": pipeline_meta,
            "error": None
        }

    except Exception as e:
        return {
            "answer": "",
            "citations": [],
            "pipeline_meta": pipeline_meta,
            "error": str(e)
        }
