# src/security/audit_logger.py
"""Audit logging to CloudWatch Logs (AWS Free Tier: 5GB/month)."""

import json
import logging
from typing import Dict, Any, Optional
import os
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Use structured logging for CloudWatch Logs Insights queries
_cw_client = None

def _get_cw_client():
    global _cw_client
    if _cw_client is None:
        try:
            import boto3
            _cw_client = boto3.client('logs', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        except Exception as e:
            logger.warning(f"CloudWatch client init failed: {e}")
    return _cw_client


@dataclass
class AuditEvent:
    """Structured audit event."""
    event_type: str  # query, index, auth, security, error
    action: str      # e.g., "query_submitted", "pii_detected", "injection_blocked"
    timestamp: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    latency_ms: Optional[int] = None


class AuditLogger:
    """
    Audit logger for security and compliance events.

    Logs to:
    1. CloudWatch Logs (production) - queryable via Logs Insights
    2. Python logger (fallback/local)
    """

    def __init__(self, log_group: str = None):
        self.log_group = log_group or os.getenv(
            'AUDIT_LOG_GROUP',
            '/aws/lambda/rag-document-assistant-api'
        )
        self.env = os.getenv('ENV', 'development')

    def log(self, event: AuditEvent) -> bool:
        """Log an audit event."""
        event_dict = asdict(event)
        event_dict['_audit'] = True  # Marker for filtering

        # Always log to Python logger (goes to CloudWatch in Lambda)
        log_line = json.dumps(event_dict, default=str)

        if event.event_type == 'security' and event.risk_score and event.risk_score > 0.5:
            logger.warning(f"AUDIT: {log_line}")
        else:
            logger.info(f"AUDIT: {log_line}")

        return True

    def log_query(
        self,
        request_id: str,
        query: str,
        user_id: str = None,
        ip_address: str = None,
        latency_ms: int = None,
        chunks_retrieved: int = None,
        pii_detected: bool = False,
        injection_risk: float = 0.0
    ):
        """Log a query event."""
        self.log(AuditEvent(
            event_type='query',
            action='query_submitted',
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            latency_ms=latency_ms,
            risk_score=injection_risk,
            details={
                'query_length': len(query) if query else 0,
                'chunks_retrieved': chunks_retrieved,
                'pii_detected': pii_detected
            }
        ))

    def log_security_event(
        self,
        action: str,
        request_id: str = None,
        risk_score: float = 0.0,
        details: Dict[str, Any] = None,
        ip_address: str = None
    ):
        """Log a security-related event."""
        self.log(AuditEvent(
            event_type='security',
            action=action,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            ip_address=ip_address,
            risk_score=risk_score,
            details=details
        ))

    def log_index_event(
        self,
        action: str,
        request_id: str = None,
        details: Dict[str, Any] = None
    ):
        """Log an indexing event."""
        self.log(AuditEvent(
            event_type='index',
            action=action,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            details=details
        ))


# Module-level singleton
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def audit_query(**kwargs):
    get_audit_logger().log_query(**kwargs)

def audit_security(**kwargs):
    get_audit_logger().log_security_event(**kwargs)

def audit_index(**kwargs):
    get_audit_logger().log_index_event(**kwargs)
