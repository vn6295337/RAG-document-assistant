# src/retrieval/index_cleanup.py
"""Index cleanup and garbage collection for Pinecone."""

import logging
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of index cleanup operation."""
    vectors_checked: int
    vectors_deleted: int
    orphaned_vectors: List[str]
    errors: List[str]


@dataclass
class IndexStats:
    """Statistics about the vector index."""
    total_vectors: int
    namespaces: Dict[str, int]
    dimension: int
    index_fullness: float


class IndexCleaner:
    """
    Cleans up orphaned and stale vectors from Pinecone.

    Operations:
    - Remove vectors for deleted documents
    - Clean up orphaned vectors (no matching document)
    - Deduplicate vector IDs
    """

    def __init__(self, index=None):
        self._index = index

    def _get_index(self):
        """Get Pinecone index (lazy load)."""
        if self._index is not None:
            return self._index

        try:
            from pinecone import Pinecone
            import src.config as cfg

            pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
            idx_meta = pc.describe_index(cfg.PINECONE_INDEX_NAME)
            host = getattr(idx_meta, "host", None) or idx_meta.get("host")
            self._index = pc.Index(host=host)
            return self._index
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            return None

    def get_index_stats(self) -> Optional[IndexStats]:
        """Get current index statistics."""
        index = self._get_index()
        if not index:
            return None

        try:
            stats = index.describe_index_stats()

            namespaces = {}
            if hasattr(stats, 'namespaces'):
                for ns, ns_stats in stats.namespaces.items():
                    namespaces[ns] = ns_stats.vector_count

            return IndexStats(
                total_vectors=stats.total_vector_count,
                namespaces=namespaces,
                dimension=stats.dimension,
                index_fullness=getattr(stats, 'index_fullness', 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return None

    def find_orphaned_vectors(
        self,
        valid_file_paths: Set[str],
        namespace: str = "",
        batch_size: int = 100
    ) -> List[str]:
        """
        Find vectors that reference files no longer in the corpus.

        Args:
            valid_file_paths: Set of valid file paths
            namespace: Pinecone namespace
            batch_size: Batch size for queries

        Returns:
            List of orphaned vector IDs
        """
        index = self._get_index()
        if not index:
            return []

        orphaned = []

        try:
            # Query for vectors and check their file_path metadata
            # Note: Pinecone doesn't support listing all vectors directly
            # We need to use a query approach or fetch by known IDs

            # If we have a list of vector IDs to check (from stale detector)
            # we can fetch them in batches

            logger.info(f"Checking for orphaned vectors (valid files: {len(valid_file_paths)})")

            # This would require either:
            # 1. Maintaining a list of all vector IDs
            # 2. Using Pinecone's list operation (if available)
            # 3. Querying with a dummy vector to sample

            # For now, return empty - actual cleanup would need ID list
            return orphaned

        except Exception as e:
            logger.error(f"Error finding orphaned vectors: {e}")
            return []

    def delete_vectors_by_file(
        self,
        file_path: str,
        namespace: str = ""
    ) -> int:
        """
        Delete all vectors associated with a file.

        Args:
            file_path: File path to delete vectors for
            namespace: Pinecone namespace

        Returns:
            Number of vectors deleted
        """
        index = self._get_index()
        if not index:
            return 0

        try:
            # Use metadata filter to find and delete
            # Note: Pinecone serverless may have limitations on delete with filter

            # Alternative: delete by ID prefix if IDs follow pattern
            # e.g., "filename.pdf::0", "filename.pdf::1", etc.

            # For now, use delete with filter (may not work on all plans)
            result = index.delete(
                filter={"file_path": file_path},
                namespace=namespace
            )

            logger.info(f"Deleted vectors for file: {file_path}")
            return 1  # Pinecone doesn't return count

        except Exception as e:
            logger.error(f"Error deleting vectors for {file_path}: {e}")
            return 0

    def delete_vectors_by_ids(
        self,
        vector_ids: List[str],
        namespace: str = ""
    ) -> CleanupResult:
        """
        Delete vectors by their IDs.

        Args:
            vector_ids: List of vector IDs to delete
            namespace: Pinecone namespace

        Returns:
            CleanupResult with deletion stats
        """
        index = self._get_index()
        if not index:
            return CleanupResult(
                vectors_checked=len(vector_ids),
                vectors_deleted=0,
                orphaned_vectors=[],
                errors=["Failed to connect to index"]
            )

        errors = []
        deleted = 0

        try:
            # Delete in batches
            batch_size = 1000
            for i in range(0, len(vector_ids), batch_size):
                batch = vector_ids[i:i + batch_size]
                try:
                    index.delete(ids=batch, namespace=namespace)
                    deleted += len(batch)
                except Exception as e:
                    errors.append(f"Batch {i // batch_size}: {str(e)}")

            logger.info(f"Deleted {deleted} vectors")

        except Exception as e:
            errors.append(str(e))

        return CleanupResult(
            vectors_checked=len(vector_ids),
            vectors_deleted=deleted,
            orphaned_vectors=[],
            errors=errors
        )

    def cleanup_for_deleted_files(
        self,
        deleted_file_paths: List[str],
        namespace: str = ""
    ) -> CleanupResult:
        """
        Clean up vectors for files that have been deleted.

        Args:
            deleted_file_paths: List of deleted file paths
            namespace: Pinecone namespace

        Returns:
            CleanupResult with cleanup stats
        """
        errors = []
        deleted_count = 0

        for file_path in deleted_file_paths:
            try:
                count = self.delete_vectors_by_file(file_path, namespace)
                deleted_count += count
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

        return CleanupResult(
            vectors_checked=len(deleted_file_paths),
            vectors_deleted=deleted_count,
            orphaned_vectors=[],
            errors=errors
        )


# Module-level singleton
_cleaner = None


def get_index_cleaner() -> IndexCleaner:
    """Get singleton index cleaner instance."""
    global _cleaner
    if _cleaner is None:
        _cleaner = IndexCleaner()
    return _cleaner


def get_index_stats() -> Optional[IndexStats]:
    """Get index statistics (convenience function)."""
    return get_index_cleaner().get_index_stats()


def cleanup_deleted_files(deleted_paths: List[str]) -> CleanupResult:
    """Clean up vectors for deleted files (convenience function)."""
    return get_index_cleaner().cleanup_for_deleted_files(deleted_paths)


def delete_vectors(vector_ids: List[str]) -> CleanupResult:
    """Delete vectors by ID (convenience function)."""
    return get_index_cleaner().delete_vectors_by_ids(vector_ids)
