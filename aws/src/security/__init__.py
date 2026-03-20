# Security module for PII handling, input validation, output moderation, audit, and RBAC (AWS track only)
from src.security.pii_handler import PIIHandler, PIIResult, scrub_pii, detect_pii
from src.security.input_guard import InputGuard, ValidationResult, validate_input, sanitize_input
from src.security.output_guard import OutputGuard, ModerationResult, moderate_output
from src.security.audit_logger import (
    AuditLogger, AuditEvent, get_audit_logger,
    audit_query, audit_security, audit_index
)
from src.security.rbac import (
    Permission,
    Role,
    User,
    ROLES,
    AccessCheckResult,
    RBACManager,
    get_rbac_manager,
    check_permission,
    check_query_access,
    add_user,
    get_user_limits
)

__all__ = [
    # PII
    "PIIHandler", "PIIResult", "scrub_pii", "detect_pii",
    # Input Guard
    "InputGuard", "ValidationResult", "validate_input", "sanitize_input",
    # Output Guard
    "OutputGuard", "ModerationResult", "moderate_output",
    # Audit
    "AuditLogger", "AuditEvent", "get_audit_logger",
    "audit_query", "audit_security", "audit_index",
    # RBAC
    "Permission", "Role", "User", "ROLES", "AccessCheckResult",
    "RBACManager", "get_rbac_manager", "check_permission",
    "check_query_access", "add_user", "get_user_limits",
]
