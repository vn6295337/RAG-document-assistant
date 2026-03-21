# src/api/security_middleware.py
"""Security middleware for AWS track - wires security guards into API routes."""

import time
import uuid
import logging
from typing import Callable, Dict, Any, Optional
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityContext:
    """Security context for a request."""
    request_id: str
    pii_detected: bool = False
    pii_scrubbed: bool = False
    injection_risk: float = 0.0
    injection_blocked: bool = False
    output_flagged: bool = False
    latency_ms: int = 0


def get_security_guards():
    """Lazy load security guards to avoid import errors when not available."""
    try:
        from src.security import (
            validate_input, sanitize_input, detect_pii, scrub_pii,
            moderate_output, audit_query, audit_security
        )
        return {
            'validate_input': validate_input,
            'sanitize_input': sanitize_input,
            'detect_pii': detect_pii,
            'scrub_pii': scrub_pii,
            'moderate_output': moderate_output,
            'audit_query': audit_query,
            'audit_security': audit_security,
            'available': True
        }
    except ImportError as e:
        logger.warning(f"Security guards not available: {e}")
        return {'available': False}


def secure_query_request(
    query: str,
    request_id: str = None,
    ip_address: str = None,
    block_on_injection: bool = True,
    scrub_pii_input: bool = True
) -> tuple[str, SecurityContext, Optional[Dict]]:
    """
    Process query through security pipeline before RAG processing.

    Returns:
        (processed_query, security_context, error_response)
        error_response is None if request should proceed, else dict to return
    """
    guards = get_security_guards()
    ctx = SecurityContext(request_id=request_id or str(uuid.uuid4()))

    if not guards.get('available'):
        return query, ctx, None

    start = time.time()
    processed_query = query

    # 1. Input validation (prompt injection detection)
    validation = guards['validate_input'](query)
    ctx.injection_risk = validation.risk_score

    if not validation.is_safe:
        ctx.injection_blocked = True
        guards['audit_security'](
            action='injection_blocked',
            request_id=ctx.request_id,
            risk_score=validation.risk_score,
            details={'flags': validation.flags},
            ip_address=ip_address
        )

        if block_on_injection and validation.risk_score >= 0.8:
            ctx.latency_ms = int((time.time() - start) * 1000)
            return query, ctx, {
                'error': 'Query blocked by security policy',
                'answer': '',
                'security': {
                    'blocked': True,
                    'reason': 'potential_injection',
                    'request_id': ctx.request_id
                }
            }

        # Sanitize high-risk queries that pass threshold
        processed_query = guards['sanitize_input'](query)

    # 2. PII detection and optional scrubbing
    pii_result = guards['detect_pii'](processed_query)
    ctx.pii_detected = pii_result.has_pii

    if pii_result.has_pii and scrub_pii_input:
        processed_query = guards['scrub_pii'](processed_query)
        ctx.pii_scrubbed = True

    ctx.latency_ms = int((time.time() - start) * 1000)
    return processed_query, ctx, None


def secure_query_response(
    answer: str,
    source_chunks: list = None,
    security_ctx: SecurityContext = None,
    scrub_pii_output: bool = True,
    ip_address: str = None
) -> tuple[str, Dict[str, Any]]:
    """
    Process RAG response through output security pipeline.

    Returns:
        (processed_answer, security_metadata)
    """
    guards = get_security_guards()
    ctx = security_ctx or SecurityContext(request_id=str(uuid.uuid4()))
    security_meta = {}

    if not guards.get('available'):
        return answer, security_meta

    start = time.time()
    processed_answer = answer

    # 1. Output moderation
    mod_result = guards['moderate_output'](answer, source_chunks or [])

    if not mod_result.is_safe:
        ctx.output_flagged = True
        processed_answer = mod_result.filtered_text or answer
        security_meta['output_flags'] = mod_result.flags

        guards['audit_security'](
            action='output_moderated',
            request_id=ctx.request_id,
            risk_score=0.5,
            details={'flags': mod_result.flags},
            ip_address=ip_address
        )

    # 2. PII scrubbing on output
    if scrub_pii_output:
        pii_result = guards['detect_pii'](processed_answer)
        if pii_result.has_pii:
            processed_answer = guards['scrub_pii'](processed_answer)
            security_meta['output_pii_scrubbed'] = True

    # 3. Audit the complete query
    guards['audit_query'](
        request_id=ctx.request_id,
        query="[query]",  # Don't log actual query content
        latency_ms=ctx.latency_ms + int((time.time() - start) * 1000),
        pii_detected=ctx.pii_detected,
        injection_risk=ctx.injection_risk,
        ip_address=ip_address
    )

    security_meta['request_id'] = ctx.request_id
    return processed_answer, security_meta


async def apply_security_to_query_request(
    request: Dict[str, Any],
    ip_address: str = None
) -> tuple[Dict[str, Any], SecurityContext, Optional[Dict]]:
    """
    Apply full security pipeline to a query request dict.

    Used by /query-secure endpoint.

    Returns:
        (modified_request, security_context, error_response)
    """
    query = request.get('query', '')
    request_id = str(uuid.uuid4())

    processed_query, ctx, error = secure_query_request(
        query=query,
        request_id=request_id,
        ip_address=ip_address,
        block_on_injection=True,
        scrub_pii_input=True
    )

    if error:
        return request, ctx, error

    # Return modified request with processed query
    modified_request = {**request, 'query': processed_query}
    return modified_request, ctx, None


def create_secure_response(
    result: Dict[str, Any],
    source_chunks: list = None,
    security_ctx: SecurityContext = None,
    ip_address: str = None
) -> Dict[str, Any]:
    """
    Apply security to RAG response and add security metadata.

    Returns modified response dict with security info.
    """
    answer = result.get('answer', '')

    processed_answer, security_meta = secure_query_response(
        answer=answer,
        source_chunks=source_chunks,
        security_ctx=security_ctx,
        scrub_pii_output=True,
        ip_address=ip_address
    )

    # Build response
    response = {**result, 'answer': processed_answer}

    # Add security metadata
    if security_meta:
        response['security'] = security_meta

    return response


# HyDE integration helper
def apply_hyde_if_available(
    query: str,
    search_fn: Callable,
    use_hyde: bool = True
) -> Dict[str, Any]:
    """
    Apply HyDE search if available (AWS track only).

    Returns search results with HyDE metadata.
    """
    try:
        from src.retrieval.hyde import hyde_search
        return hyde_search(
            query=query,
            search_fn=search_fn,
            use_hyde=use_hyde,
            combine_results=True
        )
    except ImportError:
        # HyDE not available, use direct search
        return {
            'hyde_used': False,
            'results': search_fn(query)
        }
