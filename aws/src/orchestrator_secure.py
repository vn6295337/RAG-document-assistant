# src/orchestrator_secure.py
"""
AWS-specific secure orchestrator wrapper.

Wraps the existing orchestrator with security guards:
- Input validation (prompt injection detection)
- PII detection and scrubbing
- Output moderation
- Audit logging
- HyDE retrieval enhancement
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _get_security_available() -> bool:
    """Check if security modules are available."""
    try:
        from src.security import validate_input, detect_pii
        return True
    except ImportError:
        return False


async def orchestrate_zero_storage_secure(
    query: str,
    access_token: str,
    top_k: int = 3,
    use_rewriting: bool = True,
    rewrite_strategy: str = "auto",
    use_reranking: bool = True,
    use_context_shaping: bool = True,
    token_budget: int = 2000,
    use_hyde: bool = False,
    llm_params: Dict[str, Any] = None,
    # Security options
    enable_security: bool = True,
    block_high_risk_injection: bool = True,
    scrub_pii_input: bool = True,
    scrub_pii_output: bool = True,
    ip_address: str = None
) -> Dict[str, Any]:
    """
    Secure Zero-Storage RAG orchestration with security guards.

    Extends orchestrate_zero_storage with:
    - Prompt injection detection and blocking
    - PII detection and optional scrubbing
    - Output moderation
    - Audit logging

    Args:
        query: User query
        access_token: Dropbox OAuth token
        top_k: Number of chunks to retrieve
        use_rewriting: Enable query rewriting
        rewrite_strategy: Rewriting strategy
        use_reranking: Enable cross-encoder reranking
        use_context_shaping: Enable token budget management
        token_budget: Maximum tokens for context
        use_hyde: Enable HyDE (Hypothetical Document Embeddings)
        llm_params: LLM parameters
        enable_security: Enable security guards (disable for debugging)
        block_high_risk_injection: Block queries with high injection risk
        scrub_pii_input: Remove PII from input query
        scrub_pii_output: Remove PII from output answer
        ip_address: Client IP for audit logging

    Returns:
        Dict with answer, citations, security metadata, and pipeline info
    """
    from src.orchestrator import orchestrate_zero_storage

    request_id = str(uuid.uuid4())
    start_time = time.time()

    security_meta = {
        "request_id": request_id,
        "security_enabled": enable_security
    }

    processed_query = query
    source_chunks = []

    # Security pre-processing
    if enable_security and _get_security_available():
        try:
            from src.security import (
                validate_input, sanitize_input, detect_pii, scrub_pii,
                audit_query, audit_security
            )

            # 1. Prompt injection detection
            validation = validate_input(query)
            security_meta["injection_risk"] = validation.risk_score
            security_meta["injection_flags"] = validation.flags

            if not validation.is_safe:
                audit_security(
                    action="injection_detected",
                    request_id=request_id,
                    risk_score=validation.risk_score,
                    details={"flags": validation.flags},
                    ip_address=ip_address
                )

                # Block high-risk injections
                if block_high_risk_injection and validation.risk_score >= 0.8:
                    security_meta["blocked"] = True
                    security_meta["block_reason"] = "high_risk_injection"

                    audit_security(
                        action="query_blocked",
                        request_id=request_id,
                        risk_score=validation.risk_score,
                        details={"reason": "injection_threshold_exceeded"},
                        ip_address=ip_address
                    )

                    return {
                        "answer": "",
                        "citations": [],
                        "error": "Query blocked by security policy",
                        "security": security_meta
                    }

                # Sanitize medium-risk queries
                processed_query = sanitize_input(query)
                security_meta["query_sanitized"] = True

            # 2. PII detection
            pii_result = detect_pii(processed_query)
            security_meta["pii_detected"] = pii_result.has_pii

            if pii_result.has_pii:
                security_meta["pii_entities"] = [
                    {"type": e.get("entity_type"), "score": e.get("score")}
                    for e in pii_result.entities[:5]  # Limit to first 5
                ]

                if scrub_pii_input:
                    processed_query = scrub_pii(processed_query)
                    security_meta["pii_scrubbed_input"] = True

        except Exception as e:
            logger.warning(f"Security pre-processing error: {e}")
            security_meta["security_error"] = str(e)[:100]

    # Call the base orchestrator
    try:
        result = await orchestrate_zero_storage(
            query=processed_query,
            access_token=access_token,
            top_k=top_k,
            use_rewriting=use_rewriting,
            rewrite_strategy=rewrite_strategy,
            use_reranking=use_reranking,
            use_context_shaping=use_context_shaping,
            token_budget=token_budget,
            llm_params=llm_params
        )
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        return {
            "answer": "",
            "citations": [],
            "error": str(e),
            "security": security_meta
        }

    answer = result.get("answer", "")
    source_chunks = [c.get("snippet", "") for c in result.get("citations", [])]

    # Security post-processing
    if enable_security and _get_security_available() and answer:
        try:
            from src.security import moderate_output, detect_pii, scrub_pii, audit_query

            # 3. Output moderation
            mod_result = moderate_output(answer, source_chunks)
            security_meta["output_safe"] = mod_result.is_safe
            security_meta["output_flags"] = mod_result.flags

            if not mod_result.is_safe:
                answer = mod_result.filtered_text or answer
                security_meta["output_filtered"] = True

            # 4. PII scrubbing on output
            if scrub_pii_output:
                output_pii = detect_pii(answer)
                if output_pii.has_pii:
                    answer = scrub_pii(answer)
                    security_meta["pii_scrubbed_output"] = True

            # 5. Audit logging
            latency_ms = int((time.time() - start_time) * 1000)
            audit_query(
                request_id=request_id,
                query="[redacted]",  # Don't log query content
                latency_ms=latency_ms,
                chunks_retrieved=len(result.get("citations", [])),
                pii_detected=security_meta.get("pii_detected", False),
                injection_risk=security_meta.get("injection_risk", 0.0),
                ip_address=ip_address
            )

        except Exception as e:
            logger.warning(f"Security post-processing error: {e}")
            security_meta["post_security_error"] = str(e)[:100]

    # Build final response
    response = {
        "answer": answer,
        "citations": result.get("citations", []),
        "pipeline_meta": result.get("pipeline_meta", {}),
        "security": security_meta,
        "error": result.get("error")
    }

    return response


def orchestrate_query_secure(
    query: str,
    top_k: int = 3,
    llm_params: Dict[str, Any] = None,
    rewrite_strategy: str = "auto",
    use_hybrid: bool = True,
    use_reranking: bool = True,
    chunks_path: str = None,
    # Security options
    enable_security: bool = True,
    block_high_risk_injection: bool = True,
    scrub_pii: bool = True,
    ip_address: str = None
) -> Dict[str, Any]:
    """
    Secure version of orchestrate_query with security guards.

    Synchronous version for non-Dropbox queries.
    """
    from src.orchestrator import orchestrate_query

    request_id = str(uuid.uuid4())
    start_time = time.time()

    security_meta = {
        "request_id": request_id,
        "security_enabled": enable_security
    }

    processed_query = query

    # Security pre-processing
    if enable_security and _get_security_available():
        try:
            from src.security import (
                validate_input, sanitize_input, detect_pii, scrub_pii as do_scrub,
                audit_query as log_audit, audit_security
            )

            # Input validation
            validation = validate_input(query)
            security_meta["injection_risk"] = validation.risk_score

            if not validation.is_safe:
                audit_security(
                    action="injection_detected",
                    request_id=request_id,
                    risk_score=validation.risk_score,
                    details={"flags": validation.flags},
                    ip_address=ip_address
                )

                if block_high_risk_injection and validation.risk_score >= 0.8:
                    return {
                        "answer": "",
                        "sources": [],
                        "citations": [],
                        "error": "Query blocked by security policy",
                        "security": security_meta
                    }

                processed_query = sanitize_input(query)

            # PII handling
            if scrub_pii:
                pii_result = detect_pii(processed_query)
                if pii_result.has_pii:
                    processed_query = do_scrub(processed_query)
                    security_meta["pii_scrubbed"] = True

        except Exception as e:
            logger.warning(f"Security error: {e}")

    # Call base orchestrator
    result = orchestrate_query(
        query=processed_query,
        top_k=top_k,
        llm_params=llm_params,
        rewrite_strategy=rewrite_strategy,
        use_hybrid=use_hybrid,
        use_reranking=use_reranking,
        chunks_path=chunks_path
    )

    # Post-processing
    if enable_security and _get_security_available():
        try:
            from src.security import moderate_output, scrub_pii as do_scrub, audit_query as log_audit

            answer = result.get("answer", "")
            source_chunks = [s.get("snippet", "") for s in result.get("sources", [])]

            # Output moderation
            mod_result = moderate_output(answer, source_chunks)
            if not mod_result.is_safe:
                result["answer"] = mod_result.filtered_text or answer
                security_meta["output_filtered"] = True

            # Audit
            latency_ms = int((time.time() - start_time) * 1000)
            log_audit(
                request_id=request_id,
                query="[redacted]",
                latency_ms=latency_ms,
                chunks_retrieved=len(result.get("sources", [])),
                pii_detected=security_meta.get("pii_scrubbed", False),
                injection_risk=security_meta.get("injection_risk", 0.0)
            )

        except Exception as e:
            logger.warning(f"Post-security error: {e}")

    result["security"] = security_meta
    return result
