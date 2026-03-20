# src/security/rbac.py
"""Role-based access control for multi-user RAG access."""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Available permissions."""
    # Query permissions
    QUERY_READ = "query:read"
    QUERY_ADVANCED = "query:advanced"  # HyDE, reranking, etc.

    # Document permissions
    DOCS_READ = "docs:read"
    DOCS_WRITE = "docs:write"
    DOCS_DELETE = "docs:delete"

    # Index permissions
    INDEX_READ = "index:read"
    INDEX_WRITE = "index:write"
    INDEX_DELETE = "index:delete"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"
    ADMIN_AUDIT = "admin:audit"

    # API permissions
    API_RATE_UNLIMITED = "api:rate_unlimited"
    API_BATCH = "api:batch"


@dataclass
class Role:
    """User role definition."""
    name: str
    description: str
    permissions: Set[Permission]
    token_limit_daily: int = 100000  # Daily token limit
    rate_limit_rpm: int = 60  # Requests per minute
    max_query_length: int = 1000
    max_top_k: int = 10


@dataclass
class User:
    """User definition."""
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


# Predefined roles (personas)
ROLES: Dict[str, Role] = {
    # Viewer: Read-only access, basic queries
    "viewer": Role(
        name="viewer",
        description="Read-only access with basic query capabilities",
        permissions={
            Permission.QUERY_READ,
            Permission.DOCS_READ,
            Permission.INDEX_READ,
        },
        token_limit_daily=50000,
        rate_limit_rpm=30,
        max_query_length=500,
        max_top_k=5
    ),

    # Analyst: Can run advanced queries, read all docs
    "analyst": Role(
        name="analyst",
        description="Advanced query access for data analysis",
        permissions={
            Permission.QUERY_READ,
            Permission.QUERY_ADVANCED,
            Permission.DOCS_READ,
            Permission.INDEX_READ,
            Permission.API_BATCH,
        },
        token_limit_daily=200000,
        rate_limit_rpm=60,
        max_query_length=2000,
        max_top_k=20
    ),

    # Editor: Can manage documents and index
    "editor": Role(
        name="editor",
        description="Document management and indexing capabilities",
        permissions={
            Permission.QUERY_READ,
            Permission.QUERY_ADVANCED,
            Permission.DOCS_READ,
            Permission.DOCS_WRITE,
            Permission.DOCS_DELETE,
            Permission.INDEX_READ,
            Permission.INDEX_WRITE,
            Permission.API_BATCH,
        },
        token_limit_daily=500000,
        rate_limit_rpm=120,
        max_query_length=5000,
        max_top_k=50
    ),

    # Admin: Full access
    "admin": Role(
        name="admin",
        description="Full administrative access",
        permissions={p for p in Permission},  # All permissions
        token_limit_daily=1000000,
        rate_limit_rpm=300,
        max_query_length=10000,
        max_top_k=100
    ),
}


@dataclass
class AccessCheckResult:
    """Result of access check."""
    allowed: bool
    reason: str
    user: Optional[User] = None
    role: Optional[Role] = None
    missing_permissions: List[Permission] = field(default_factory=list)


class RBACManager:
    """
    Manages role-based access control.

    Features:
    - Role-based permissions
    - Token and rate limits per role
    - Query parameter restrictions
    - Audit logging integration
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._roles = ROLES.copy()

    def add_user(
        self,
        user_id: str,
        email: str,
        name: str,
        role: str = "viewer",
        metadata: Dict[str, Any] = None
    ) -> User:
        """Add a new user."""
        if role not in self._roles:
            raise ValueError(f"Unknown role: {role}")

        user = User(
            user_id=user_id,
            email=email,
            name=name,
            role=role,
            metadata=metadata or {}
        )
        self._users[user_id] = user
        logger.info(f"User added: {user_id} with role {role}")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    def get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name."""
        return self._roles.get(role_name)

    def check_permission(
        self,
        user_id: str,
        required_permissions: List[Permission]
    ) -> AccessCheckResult:
        """
        Check if a user has required permissions.

        Args:
            user_id: User identifier
            required_permissions: List of required permissions

        Returns:
            AccessCheckResult with access decision
        """
        user = self.get_user(user_id)
        if not user:
            return AccessCheckResult(
                allowed=False,
                reason="User not found"
            )

        if not user.is_active:
            return AccessCheckResult(
                allowed=False,
                reason="User account is inactive",
                user=user
            )

        role = self.get_role(user.role)
        if not role:
            return AccessCheckResult(
                allowed=False,
                reason=f"Unknown role: {user.role}",
                user=user
            )

        # Check permissions
        missing = [p for p in required_permissions if p not in role.permissions]

        if missing:
            return AccessCheckResult(
                allowed=False,
                reason=f"Missing permissions: {[p.value for p in missing]}",
                user=user,
                role=role,
                missing_permissions=missing
            )

        return AccessCheckResult(
            allowed=True,
            reason="Access granted",
            user=user,
            role=role
        )

    def check_query_access(
        self,
        user_id: str,
        query_length: int,
        top_k: int,
        use_advanced: bool = False
    ) -> AccessCheckResult:
        """
        Check if a user can perform a query with given parameters.

        Args:
            user_id: User identifier
            query_length: Length of query string
            top_k: Requested top_k value
            use_advanced: Using advanced features (HyDE, reranking)

        Returns:
            AccessCheckResult with access decision
        """
        # Check basic permission
        required = [Permission.QUERY_READ]
        if use_advanced:
            required.append(Permission.QUERY_ADVANCED)

        result = self.check_permission(user_id, required)
        if not result.allowed:
            return result

        role = result.role

        # Check parameter limits
        if query_length > role.max_query_length:
            return AccessCheckResult(
                allowed=False,
                reason=f"Query too long: {query_length} > {role.max_query_length}",
                user=result.user,
                role=role
            )

        if top_k > role.max_top_k:
            return AccessCheckResult(
                allowed=False,
                reason=f"top_k too high: {top_k} > {role.max_top_k}",
                user=result.user,
                role=role
            )

        return result

    def check_document_access(
        self,
        user_id: str,
        action: str  # read, write, delete
    ) -> AccessCheckResult:
        """Check document access permission."""
        permission_map = {
            "read": Permission.DOCS_READ,
            "write": Permission.DOCS_WRITE,
            "delete": Permission.DOCS_DELETE
        }
        perm = permission_map.get(action)
        if not perm:
            return AccessCheckResult(allowed=False, reason=f"Unknown action: {action}")

        return self.check_permission(user_id, [perm])

    def check_index_access(
        self,
        user_id: str,
        action: str  # read, write, delete
    ) -> AccessCheckResult:
        """Check index access permission."""
        permission_map = {
            "read": Permission.INDEX_READ,
            "write": Permission.INDEX_WRITE,
            "delete": Permission.INDEX_DELETE
        }
        perm = permission_map.get(action)
        if not perm:
            return AccessCheckResult(allowed=False, reason=f"Unknown action: {action}")

        return self.check_permission(user_id, [perm])

    def get_user_limits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get rate and token limits for a user."""
        user = self.get_user(user_id)
        if not user:
            return None

        role = self.get_role(user.role)
        if not role:
            return None

        return {
            "token_limit_daily": role.token_limit_daily,
            "rate_limit_rpm": role.rate_limit_rpm,
            "max_query_length": role.max_query_length,
            "max_top_k": role.max_top_k
        }

    def add_custom_role(self, role: Role):
        """Add a custom role."""
        self._roles[role.name] = role
        logger.info(f"Custom role added: {role.name}")

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update a user's role."""
        user = self.get_user(user_id)
        if not user or new_role not in self._roles:
            return False

        old_role = user.role
        user.role = new_role
        logger.info(f"User {user_id} role changed: {old_role} -> {new_role}")
        return True

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user."""
        user = self.get_user(user_id)
        if not user:
            return False

        user.is_active = False
        logger.info(f"User {user_id} deactivated")
        return True

    def list_users(self, role: str = None) -> List[User]:
        """List users, optionally filtered by role."""
        users = list(self._users.values())
        if role:
            users = [u for u in users if u.role == role]
        return users

    def list_roles(self) -> List[Role]:
        """List available roles."""
        return list(self._roles.values())


# Module-level singleton
_manager = None


def get_rbac_manager() -> RBACManager:
    """Get singleton RBAC manager instance."""
    global _manager
    if _manager is None:
        _manager = RBACManager()
    return _manager


def check_permission(user_id: str, permissions: List[Permission]) -> AccessCheckResult:
    """Check user permissions (convenience function)."""
    return get_rbac_manager().check_permission(user_id, permissions)


def check_query_access(
    user_id: str,
    query_length: int,
    top_k: int = 5,
    use_advanced: bool = False
) -> AccessCheckResult:
    """Check query access (convenience function)."""
    return get_rbac_manager().check_query_access(
        user_id, query_length, top_k, use_advanced
    )


def add_user(user_id: str, email: str, name: str, role: str = "viewer") -> User:
    """Add a user (convenience function)."""
    return get_rbac_manager().add_user(user_id, email, name, role)


def get_user_limits(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user limits (convenience function)."""
    return get_rbac_manager().get_user_limits(user_id)
