# src/retrieval/stale_detector.py
"""Stale reference detection for document lifecycle management."""

import logging
import hashlib
import json
import os
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class DocumentReference:
    """Reference to an indexed document."""
    file_path: str
    file_id: str
    content_hash: str
    indexed_at: str
    chunk_count: int
    metadata: Dict[str, Any]


@dataclass
class StaleCheckResult:
    """Result of stale reference check."""
    file_path: str
    status: str  # current, modified, deleted, unknown
    indexed_at: str
    last_checked: str
    current_hash: Optional[str] = None
    indexed_hash: Optional[str] = None
    needs_reindex: bool = False


@dataclass
class StaleReport:
    """Complete stale detection report."""
    total_documents: int
    current_count: int
    modified_count: int
    deleted_count: int
    unknown_count: int
    stale_references: List[StaleCheckResult]
    recommendations: List[str]


class StaleReferenceDetector:
    """
    Detects stale references in the vector index.

    Stale references occur when:
    - Source document is deleted
    - Source document is modified (content changed)
    - Source document is moved/renamed
    """

    def __init__(
        self,
        reference_store_path: str = None,
        staleness_threshold_days: int = 30
    ):
        self.reference_store_path = reference_store_path or os.getenv(
            "REFERENCE_STORE_PATH",
            "/tmp/document_references.json"
        )
        self.staleness_threshold_days = staleness_threshold_days
        self._references: Dict[str, DocumentReference] = {}
        self._load_references()

    def _load_references(self):
        """Load stored document references."""
        try:
            if os.path.exists(self.reference_store_path):
                with open(self.reference_store_path, "r") as f:
                    data = json.load(f)
                    for path, ref_data in data.items():
                        self._references[path] = DocumentReference(**ref_data)
        except Exception as e:
            logger.warning(f"Failed to load references: {e}")

    def _save_references(self):
        """Save document references to storage."""
        try:
            data = {path: asdict(ref) for path, ref in self._references.items()}
            with open(self.reference_store_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save references: {e}")

    def compute_content_hash(self, content: str) -> str:
        """Compute hash of document content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def register_document(
        self,
        file_path: str,
        file_id: str,
        content: str,
        chunk_count: int,
        metadata: Dict[str, Any] = None
    ) -> DocumentReference:
        """
        Register a document after indexing.

        Call this after successfully indexing a document.
        """
        ref = DocumentReference(
            file_path=file_path,
            file_id=file_id,
            content_hash=self.compute_content_hash(content),
            indexed_at=datetime.utcnow().isoformat(),
            chunk_count=chunk_count,
            metadata=metadata or {}
        )
        self._references[file_path] = ref
        self._save_references()
        return ref

    def unregister_document(self, file_path: str) -> bool:
        """Remove a document reference after deletion."""
        if file_path in self._references:
            del self._references[file_path]
            self._save_references()
            return True
        return False

    def check_document(
        self,
        file_path: str,
        current_content: Optional[str] = None
    ) -> StaleCheckResult:
        """
        Check if a document reference is stale.

        Args:
            file_path: Path to the document
            current_content: Current content (if available)

        Returns:
            StaleCheckResult with status
        """
        now = datetime.utcnow().isoformat()

        if file_path not in self._references:
            return StaleCheckResult(
                file_path=file_path,
                status="unknown",
                indexed_at="",
                last_checked=now,
                needs_reindex=True
            )

        ref = self._references[file_path]

        if current_content is None:
            # Content not provided - can't determine if modified
            return StaleCheckResult(
                file_path=file_path,
                status="unknown",
                indexed_at=ref.indexed_at,
                last_checked=now,
                indexed_hash=ref.content_hash,
                needs_reindex=False
            )

        current_hash = self.compute_content_hash(current_content)

        if current_hash == ref.content_hash:
            return StaleCheckResult(
                file_path=file_path,
                status="current",
                indexed_at=ref.indexed_at,
                last_checked=now,
                current_hash=current_hash,
                indexed_hash=ref.content_hash,
                needs_reindex=False
            )
        else:
            return StaleCheckResult(
                file_path=file_path,
                status="modified",
                indexed_at=ref.indexed_at,
                last_checked=now,
                current_hash=current_hash,
                indexed_hash=ref.content_hash,
                needs_reindex=True
            )

    def check_deleted(
        self,
        existing_paths: Set[str]
    ) -> List[StaleCheckResult]:
        """
        Find references to deleted documents.

        Args:
            existing_paths: Set of paths that currently exist

        Returns:
            List of results for deleted documents
        """
        deleted = []
        now = datetime.utcnow().isoformat()

        for path, ref in self._references.items():
            if path not in existing_paths:
                deleted.append(StaleCheckResult(
                    file_path=path,
                    status="deleted",
                    indexed_at=ref.indexed_at,
                    last_checked=now,
                    indexed_hash=ref.content_hash,
                    needs_reindex=False  # Need to remove, not reindex
                ))

        return deleted

    def check_age(self) -> List[StaleCheckResult]:
        """Find documents that haven't been checked recently."""
        stale_by_age = []
        now = datetime.utcnow()
        threshold = now - timedelta(days=self.staleness_threshold_days)

        for path, ref in self._references.items():
            try:
                indexed_date = datetime.fromisoformat(ref.indexed_at.replace("Z", ""))
                if indexed_date < threshold:
                    stale_by_age.append(StaleCheckResult(
                        file_path=path,
                        status="aged",
                        indexed_at=ref.indexed_at,
                        last_checked=now.isoformat(),
                        indexed_hash=ref.content_hash,
                        needs_reindex=True  # Should re-verify
                    ))
            except Exception:
                continue

        return stale_by_age

    def generate_report(
        self,
        check_results: List[StaleCheckResult]
    ) -> StaleReport:
        """Generate a comprehensive stale detection report."""
        current = [r for r in check_results if r.status == "current"]
        modified = [r for r in check_results if r.status == "modified"]
        deleted = [r for r in check_results if r.status == "deleted"]
        unknown = [r for r in check_results if r.status in ("unknown", "aged")]

        stale = modified + deleted + unknown

        recommendations = []
        if modified:
            recommendations.append(f"Re-index {len(modified)} modified document(s)")
        if deleted:
            recommendations.append(f"Remove {len(deleted)} deleted reference(s) from index")
        if unknown:
            recommendations.append(f"Verify {len(unknown)} document(s) with unknown status")
        if not stale:
            recommendations.append("All documents are current. No action needed.")

        return StaleReport(
            total_documents=len(check_results),
            current_count=len(current),
            modified_count=len(modified),
            deleted_count=len(deleted),
            unknown_count=len(unknown),
            stale_references=stale,
            recommendations=recommendations
        )

    def get_registered_paths(self) -> List[str]:
        """Get all registered document paths."""
        return list(self._references.keys())

    def get_reference(self, file_path: str) -> Optional[DocumentReference]:
        """Get reference for a specific document."""
        return self._references.get(file_path)


# Module-level singleton
_detector = None


def get_stale_detector() -> StaleReferenceDetector:
    """Get singleton stale detector instance."""
    global _detector
    if _detector is None:
        _detector = StaleReferenceDetector()
    return _detector


def register_indexed_document(
    file_path: str,
    file_id: str,
    content: str,
    chunk_count: int,
    metadata: Dict[str, Any] = None
) -> DocumentReference:
    """Register a document after indexing (convenience function)."""
    return get_stale_detector().register_document(
        file_path=file_path,
        file_id=file_id,
        content=content,
        chunk_count=chunk_count,
        metadata=metadata
    )


def check_for_stale_references(
    documents: List[Dict[str, Any]]
) -> StaleReport:
    """
    Check a list of documents for stale references.

    Args:
        documents: List of dicts with 'path' and 'content' keys

    Returns:
        StaleReport with findings
    """
    detector = get_stale_detector()
    results = []
    existing_paths = set()

    for doc in documents:
        path = doc.get("path", "")
        content = doc.get("content")
        if path:
            existing_paths.add(path)
            result = detector.check_document(path, content)
            results.append(result)

    # Check for deleted documents
    deleted = detector.check_deleted(existing_paths)
    results.extend(deleted)

    return detector.generate_report(results)
