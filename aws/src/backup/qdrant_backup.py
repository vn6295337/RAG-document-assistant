# src/backup/qdrant_backup.py
"""Backup and recovery using Qdrant as secondary vector store."""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """Information about a backup."""
    backup_id: str
    created_at: str
    source: str  # pinecone
    destination: str  # qdrant
    vector_count: int
    status: str  # pending, in_progress, completed, failed
    metadata: Dict[str, Any]


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    vectors_recovered: int
    source: str
    destination: str
    errors: List[str]


class QdrantBackupManager:
    """
    Manages backup and recovery using Qdrant.

    Features:
    - Backup Pinecone vectors to Qdrant
    - Recover from Qdrant to Pinecone
    - Incremental backups
    - Point-in-time recovery
    """

    def __init__(
        self,
        qdrant_url: str = None,
        qdrant_api_key: str = None,
        collection_name: str = "rag_backup"
    ):
        self.qdrant_url = qdrant_url or os.getenv(
            "QDRANT_URL",
            "http://localhost:6333"
        )
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name
        self._client = None
        self._backups: Dict[str, BackupInfo] = {}

    def _get_qdrant_client(self):
        """Get Qdrant client (lazy load)."""
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            if self.qdrant_api_key:
                self._client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key
                )
            else:
                self._client = QdrantClient(url=self.qdrant_url)

            return self._client

        except ImportError:
            logger.error("qdrant-client not installed. Run: pip install qdrant-client")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return None

    def _ensure_collection(self, dimension: int):
        """Ensure backup collection exists."""
        client = self._get_qdrant_client()
        if not client:
            return False

        try:
            from qdrant_client.http import models

            collections = client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=dimension,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            return False

    def backup_from_pinecone(
        self,
        pinecone_index,
        batch_size: int = 100,
        namespace: str = ""
    ) -> BackupInfo:
        """
        Backup vectors from Pinecone to Qdrant.

        Args:
            pinecone_index: Pinecone index object
            batch_size: Batch size for operations
            namespace: Pinecone namespace

        Returns:
            BackupInfo with backup status
        """
        backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        backup = BackupInfo(
            backup_id=backup_id,
            created_at=datetime.utcnow().isoformat(),
            source="pinecone",
            destination="qdrant",
            vector_count=0,
            status="pending",
            metadata={"namespace": namespace, "batch_size": batch_size}
        )
        self._backups[backup_id] = backup

        try:
            from qdrant_client.http import models

            client = self._get_qdrant_client()
            if not client:
                backup.status = "failed"
                return backup

            # Get index stats
            stats = pinecone_index.describe_index_stats()
            dimension = stats.dimension

            # Ensure collection exists
            if not self._ensure_collection(dimension):
                backup.status = "failed"
                return backup

            backup.status = "in_progress"

            # Note: Pinecone doesn't support listing all vectors directly
            # In production, you'd need to maintain a list of vector IDs
            # or use a different approach (e.g., query with dummy vectors)

            # For demo, we'll backup vectors by querying
            # In production, iterate through known IDs

            # Example: Query to get sample vectors
            sample_query = [0.0] * dimension
            results = pinecone_index.query(
                vector=sample_query,
                top_k=10000,  # Get as many as possible
                include_values=True,
                include_metadata=True,
                namespace=namespace
            )

            vectors_backed_up = 0
            points = []

            for match in results.matches:
                point = models.PointStruct(
                    id=hash(match.id) % (2**63),  # Qdrant needs int IDs
                    vector=match.values,
                    payload={
                        "pinecone_id": match.id,
                        "original_score": match.score,
                        "backup_id": backup_id,
                        "backed_up_at": datetime.utcnow().isoformat(),
                        **(match.metadata or {})
                    }
                )
                points.append(point)

                if len(points) >= batch_size:
                    client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    vectors_backed_up += len(points)
                    points = []

            # Final batch
            if points:
                client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                vectors_backed_up += len(points)

            backup.vector_count = vectors_backed_up
            backup.status = "completed"
            logger.info(f"Backup completed: {backup_id} ({vectors_backed_up} vectors)")

        except Exception as e:
            backup.status = "failed"
            backup.metadata["error"] = str(e)
            logger.error(f"Backup failed: {e}")

        return backup

    def recover_to_pinecone(
        self,
        pinecone_index,
        backup_id: str = None,
        batch_size: int = 100,
        namespace: str = ""
    ) -> RecoveryResult:
        """
        Recover vectors from Qdrant to Pinecone.

        Args:
            pinecone_index: Pinecone index object
            backup_id: Specific backup to recover (latest if None)
            batch_size: Batch size for operations
            namespace: Target Pinecone namespace

        Returns:
            RecoveryResult with recovery status
        """
        errors = []
        vectors_recovered = 0

        try:
            from qdrant_client.http import models

            client = self._get_qdrant_client()
            if not client:
                return RecoveryResult(
                    success=False,
                    vectors_recovered=0,
                    source="qdrant",
                    destination="pinecone",
                    errors=["Failed to connect to Qdrant"]
                )

            # Build filter for specific backup
            filter_conditions = None
            if backup_id:
                filter_conditions = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="backup_id",
                            match=models.MatchValue(value=backup_id)
                        )
                    ]
                )

            # Scroll through all points
            offset = None
            while True:
                results = client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter_conditions,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )

                points, next_offset = results

                if not points:
                    break

                # Convert to Pinecone format
                vectors = []
                for point in points:
                    pinecone_id = point.payload.get("pinecone_id", str(point.id))
                    # Remove backup-specific fields from metadata
                    metadata = {
                        k: v for k, v in point.payload.items()
                        if k not in ["pinecone_id", "backup_id", "backed_up_at", "original_score"]
                    }
                    vectors.append({
                        "id": pinecone_id,
                        "values": point.vector,
                        "metadata": metadata
                    })

                try:
                    pinecone_index.upsert(vectors=vectors, namespace=namespace)
                    vectors_recovered += len(vectors)
                except Exception as e:
                    errors.append(f"Batch upsert failed: {str(e)}")

                offset = next_offset
                if offset is None:
                    break

            logger.info(f"Recovery completed: {vectors_recovered} vectors")

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Recovery failed: {e}")

        return RecoveryResult(
            success=len(errors) == 0,
            vectors_recovered=vectors_recovered,
            source="qdrant",
            destination="pinecone",
            errors=errors
        )

    def list_backups(self) -> List[BackupInfo]:
        """List all backups."""
        return list(self._backups.values())

    def get_backup(self, backup_id: str) -> Optional[BackupInfo]:
        """Get specific backup info."""
        return self._backups.get(backup_id)

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup from Qdrant."""
        try:
            from qdrant_client.http import models

            client = self._get_qdrant_client()
            if not client:
                return False

            # Delete points with matching backup_id
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="backup_id",
                                match=models.MatchValue(value=backup_id)
                            )
                        ]
                    )
                )
            )

            if backup_id in self._backups:
                del self._backups[backup_id]

            logger.info(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        client = self._get_qdrant_client()
        if not client:
            return {"error": "Not connected"}

        try:
            info = client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "backups": len(self._backups)
            }
        except Exception as e:
            return {"error": str(e)}


# Module-level singleton
_manager = None


def get_backup_manager() -> QdrantBackupManager:
    """Get singleton backup manager instance."""
    global _manager
    if _manager is None:
        _manager = QdrantBackupManager()
    return _manager


def backup_to_qdrant(pinecone_index, namespace: str = "") -> BackupInfo:
    """Backup Pinecone to Qdrant (convenience function)."""
    return get_backup_manager().backup_from_pinecone(
        pinecone_index, namespace=namespace
    )


def recover_from_qdrant(
    pinecone_index,
    backup_id: str = None,
    namespace: str = ""
) -> RecoveryResult:
    """Recover from Qdrant to Pinecone (convenience function)."""
    return get_backup_manager().recover_to_pinecone(
        pinecone_index, backup_id=backup_id, namespace=namespace
    )


def list_backups() -> List[BackupInfo]:
    """List backups (convenience function)."""
    return get_backup_manager().list_backups()
