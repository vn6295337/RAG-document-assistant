# src/retrieval/embedding_versioning.py
"""Embedding model versioning and migration support."""

import logging
import json
import os
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingModelVersion:
    """Embedding model version metadata."""
    version_id: str
    model_name: str
    model_provider: str
    dimension: int
    created_at: str
    is_active: bool
    document_count: int
    vector_count: int
    metadata: Dict[str, Any]


@dataclass
class MigrationPlan:
    """Plan for migrating to a new embedding model."""
    source_version: str
    target_version: str
    documents_to_migrate: int
    estimated_cost: float  # API calls
    estimated_time_minutes: float
    strategy: str  # full, incremental, parallel


@dataclass
class MigrationStatus:
    """Status of an ongoing migration."""
    migration_id: str
    source_version: str
    target_version: str
    status: str  # pending, in_progress, completed, failed
    progress_pct: float
    documents_migrated: int
    documents_total: int
    started_at: str
    completed_at: Optional[str]
    errors: List[str]


class EmbeddingVersionManager:
    """
    Manages embedding model versions for safe upgrades.

    Features:
    - Track current and historical embedding versions
    - Plan and execute migrations
    - Support parallel indexes during migration
    - Rollback capability
    """

    def __init__(self, state_path: str = None):
        self.state_path = state_path or os.getenv(
            "EMBEDDING_VERSION_STATE",
            "/tmp/embedding_versions.json"
        )
        self._versions: Dict[str, EmbeddingModelVersion] = {}
        self._active_version: Optional[str] = None
        self._migrations: Dict[str, MigrationStatus] = {}
        self._load_state()

    def _load_state(self):
        """Load state from storage."""
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for vid, vdata in data.get("versions", {}).items():
                        self._versions[vid] = EmbeddingModelVersion(**vdata)
                    self._active_version = data.get("active_version")
        except Exception as e:
            logger.warning(f"Failed to load embedding version state: {e}")

    def _save_state(self):
        """Save state to storage."""
        try:
            data = {
                "versions": {vid: asdict(v) for vid, v in self._versions.items()},
                "active_version": self._active_version
            }
            with open(self.state_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save embedding version state: {e}")

    def generate_version_id(self, model_name: str, provider: str) -> str:
        """Generate a unique version ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        content = f"{model_name}:{provider}:{timestamp}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"v_{timestamp}_{hash_suffix}"

    def register_version(
        self,
        model_name: str,
        model_provider: str,
        dimension: int,
        metadata: Dict[str, Any] = None,
        set_active: bool = False
    ) -> EmbeddingModelVersion:
        """
        Register a new embedding model version.

        Args:
            model_name: Name of the embedding model
            model_provider: Provider (huggingface, openai, etc.)
            dimension: Embedding dimension
            metadata: Additional metadata
            set_active: Set as active version

        Returns:
            Created EmbeddingModelVersion
        """
        version_id = self.generate_version_id(model_name, model_provider)

        version = EmbeddingModelVersion(
            version_id=version_id,
            model_name=model_name,
            model_provider=model_provider,
            dimension=dimension,
            created_at=datetime.utcnow().isoformat(),
            is_active=set_active,
            document_count=0,
            vector_count=0,
            metadata=metadata or {}
        )

        self._versions[version_id] = version

        if set_active:
            self._set_active(version_id)

        self._save_state()
        logger.info(f"Registered embedding version: {version_id} ({model_name})")
        return version

    def _set_active(self, version_id: str):
        """Set a version as active."""
        # Deactivate current
        if self._active_version and self._active_version in self._versions:
            self._versions[self._active_version].is_active = False

        # Activate new
        if version_id in self._versions:
            self._versions[version_id].is_active = True
            self._active_version = version_id

    def get_active_version(self) -> Optional[EmbeddingModelVersion]:
        """Get the currently active version."""
        if self._active_version:
            return self._versions.get(self._active_version)
        return None

    def get_version(self, version_id: str) -> Optional[EmbeddingModelVersion]:
        """Get a specific version."""
        return self._versions.get(version_id)

    def list_versions(self) -> List[EmbeddingModelVersion]:
        """List all versions."""
        return list(self._versions.values())

    def update_counts(
        self,
        version_id: str,
        document_count: int = None,
        vector_count: int = None
    ):
        """Update document/vector counts for a version."""
        version = self._versions.get(version_id)
        if version:
            if document_count is not None:
                version.document_count = document_count
            if vector_count is not None:
                version.vector_count = vector_count
            self._save_state()

    def plan_migration(
        self,
        target_model: str,
        target_provider: str,
        target_dimension: int,
        strategy: str = "incremental"
    ) -> MigrationPlan:
        """
        Plan a migration to a new embedding model.

        Args:
            target_model: Target model name
            target_provider: Target provider
            target_dimension: Target dimension
            strategy: Migration strategy (full, incremental, parallel)

        Returns:
            MigrationPlan with estimates
        """
        current = self.get_active_version()
        if not current:
            raise ValueError("No active version to migrate from")

        # Register target version
        target = self.register_version(
            target_model, target_provider, target_dimension,
            metadata={"migration_source": current.version_id}
        )

        # Estimate costs
        docs_to_migrate = current.document_count
        # Assume ~$0.0001 per embedding call
        estimated_cost = docs_to_migrate * 0.0001
        # Assume ~100 docs per minute
        estimated_time = docs_to_migrate / 100

        return MigrationPlan(
            source_version=current.version_id,
            target_version=target.version_id,
            documents_to_migrate=docs_to_migrate,
            estimated_cost=round(estimated_cost, 2),
            estimated_time_minutes=round(estimated_time, 1),
            strategy=strategy
        )

    def start_migration(self, plan: MigrationPlan) -> MigrationStatus:
        """Start a migration based on a plan."""
        migration_id = f"mig_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        status = MigrationStatus(
            migration_id=migration_id,
            source_version=plan.source_version,
            target_version=plan.target_version,
            status="pending",
            progress_pct=0.0,
            documents_migrated=0,
            documents_total=plan.documents_to_migrate,
            started_at=datetime.utcnow().isoformat(),
            completed_at=None,
            errors=[]
        )

        self._migrations[migration_id] = status
        logger.info(f"Migration started: {migration_id}")
        return status

    def update_migration_progress(
        self,
        migration_id: str,
        documents_migrated: int,
        errors: List[str] = None
    ):
        """Update migration progress."""
        status = self._migrations.get(migration_id)
        if status:
            status.documents_migrated = documents_migrated
            status.progress_pct = (documents_migrated / status.documents_total * 100) if status.documents_total else 0
            status.status = "in_progress"
            if errors:
                status.errors.extend(errors)

    def complete_migration(self, migration_id: str, success: bool = True):
        """Complete a migration."""
        status = self._migrations.get(migration_id)
        if status:
            status.completed_at = datetime.utcnow().isoformat()
            status.status = "completed" if success else "failed"
            status.progress_pct = 100.0 if success else status.progress_pct

            if success:
                # Set target as active
                self._set_active(status.target_version)
                self._save_state()
                logger.info(f"Migration completed: {migration_id}")
            else:
                logger.error(f"Migration failed: {migration_id}")

    def rollback(self, to_version_id: str) -> bool:
        """Rollback to a previous version."""
        if to_version_id not in self._versions:
            return False

        self._set_active(to_version_id)
        self._save_state()
        logger.info(f"Rolled back to version: {to_version_id}")
        return True

    def get_migration_status(self, migration_id: str) -> Optional[MigrationStatus]:
        """Get migration status."""
        return self._migrations.get(migration_id)


# Module-level singleton
_manager = None


def get_version_manager() -> EmbeddingVersionManager:
    """Get singleton version manager instance."""
    global _manager
    if _manager is None:
        _manager = EmbeddingVersionManager()
    return _manager


def register_embedding_version(
    model_name: str,
    provider: str,
    dimension: int,
    set_active: bool = False
) -> EmbeddingModelVersion:
    """Register embedding version (convenience function)."""
    return get_version_manager().register_version(
        model_name, provider, dimension, set_active=set_active
    )


def get_active_embedding_version() -> Optional[EmbeddingModelVersion]:
    """Get active embedding version (convenience function)."""
    return get_version_manager().get_active_version()


def plan_embedding_migration(
    target_model: str,
    target_provider: str,
    target_dimension: int
) -> MigrationPlan:
    """Plan embedding migration (convenience function)."""
    return get_version_manager().plan_migration(
        target_model, target_provider, target_dimension
    )
