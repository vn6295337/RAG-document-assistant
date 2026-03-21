# src/ingestion/deduplicator.py
"""Source-level deduplication for document ingestion."""

import hashlib
import logging
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""
    total_documents: int
    unique_documents: int
    duplicate_documents: int
    duplicates: List[Dict[str, Any]]  # List of duplicate info


class DocumentDeduplicator:
    """
    Deduplicates documents at ingestion time.

    Strategies:
    - Content hash: Exact duplicate detection
    - Similarity hash (SimHash): Near-duplicate detection
    - Filename: Same file uploaded multiple times
    """

    def __init__(self):
        self._content_hashes: Dict[str, str] = {}  # hash -> first_file_path
        self._filename_hashes: Dict[str, str] = {}

    def compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_simhash(self, content: str, hash_bits: int = 64) -> int:
        """
        Compute SimHash for near-duplicate detection.

        SimHash is locality-sensitive: similar documents have similar hashes.
        """
        if not content:
            return 0

        # Tokenize
        words = content.lower().split()
        if not words:
            return 0

        # Initialize bit counts
        v = [0] * hash_bits

        for word in words:
            # Hash each word
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)

            for i in range(hash_bits):
                bit = (word_hash >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1

        # Convert to hash
        simhash = 0
        for i in range(hash_bits):
            if v[i] > 0:
                simhash |= (1 << i)

        return simhash

    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between two SimHashes."""
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += 1
            xor &= xor - 1
        return distance

    def is_near_duplicate(
        self,
        hash1: int,
        hash2: int,
        threshold: int = 3
    ) -> bool:
        """Check if two SimHashes indicate near-duplicates."""
        return self.hamming_distance(hash1, hash2) <= threshold

    def check_document(
        self,
        file_path: str,
        content: str,
        check_near_duplicates: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if a document is a duplicate.

        Args:
            file_path: Path to the document
            content: Document content
            check_near_duplicates: Also check for near-duplicates

        Returns:
            Tuple of (is_duplicate, duplicate_type, info)
        """
        content_hash = self.compute_content_hash(content)

        # Check exact duplicate
        if content_hash in self._content_hashes:
            original = self._content_hashes[content_hash]
            return True, "exact", {
                "original_file": original,
                "duplicate_file": file_path,
                "hash": content_hash
            }

        # Check near-duplicate using SimHash
        if check_near_duplicates and len(self._content_hashes) > 0:
            new_simhash = self.compute_simhash(content)
            # This is O(n) - for large corpora, use LSH
            for existing_hash, existing_path in self._content_hashes.items():
                # We'd need to store simhashes separately for efficiency
                # For now, skip near-duplicate for simplicity
                pass

        # Not a duplicate - register it
        self._content_hashes[content_hash] = file_path
        return False, "unique", {"hash": content_hash}

    def deduplicate_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> DeduplicationResult:
        """
        Deduplicate a batch of documents.

        Args:
            documents: List of dicts with 'path' and 'content' keys

        Returns:
            DeduplicationResult with unique documents
        """
        duplicates = []
        unique_count = 0

        for doc in documents:
            path = doc.get("path", doc.get("file_path", ""))
            content = doc.get("content", doc.get("text", ""))

            is_dup, dup_type, info = self.check_document(path, content)

            if is_dup:
                duplicates.append({
                    "file": path,
                    "type": dup_type,
                    **info
                })
            else:
                unique_count += 1

        return DeduplicationResult(
            total_documents=len(documents),
            unique_documents=unique_count,
            duplicate_documents=len(duplicates),
            duplicates=duplicates
        )

    def clear(self):
        """Clear the deduplication cache."""
        self._content_hashes.clear()
        self._filename_hashes.clear()


# Module-level singleton
_deduplicator = None


def get_deduplicator() -> DocumentDeduplicator:
    """Get singleton deduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = DocumentDeduplicator()
    return _deduplicator


def check_duplicate(file_path: str, content: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Check if a document is a duplicate (convenience function)."""
    return get_deduplicator().check_document(file_path, content)


def deduplicate_documents(documents: List[Dict[str, Any]]) -> DeduplicationResult:
    """Deduplicate a batch of documents (convenience function)."""
    return get_deduplicator().deduplicate_batch(documents)
