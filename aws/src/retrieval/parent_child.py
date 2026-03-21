# src/retrieval/parent_child.py
"""
Parent-child retrieval for hierarchical document chunks.

This module enables retrieval of larger context windows by
linking child chunks to their parent sections.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParentChildChunk:
    """A chunk with parent-child relationships."""
    id: str
    text: str
    parent_id: Optional[str]
    children_ids: List[str]
    level: int  # 0 = root/document, 1 = section, 2 = paragraph, 3 = sentence
    metadata: Dict[str, Any]


@dataclass
class HierarchicalResult:
    """Result with hierarchical context."""
    chunks: List[Dict[str, Any]]
    parent_chunks: List[Dict[str, Any]]
    context_expanded: bool
    expansion_strategy: str


class ParentChildRetriever:
    """
    Retriever that can expand results to include parent context.

    Strategies:
    - child_to_parent: Retrieve child chunks, expand to parents
    - parent_first: Search parents, include children
    - hybrid: Search both, deduplicate
    """

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap

    def create_hierarchy(
        self,
        document_text: str,
        document_id: str,
        metadata: Dict[str, Any] = None
    ) -> List[ParentChildChunk]:
        """
        Create hierarchical chunks from a document.

        Creates two levels:
        - Parent chunks (larger, ~2000 chars)
        - Child chunks (smaller, ~500 chars)

        Args:
            document_text: Full document text
            document_id: Unique document identifier
            metadata: Additional metadata

        Returns:
            List of ParentChildChunk with relationships
        """
        if not document_text:
            return []

        metadata = metadata or {}
        chunks = []

        # Split into parent-level chunks
        parent_chunks = self._split_into_chunks(
            document_text,
            self.parent_chunk_size,
            self.overlap
        )

        for parent_idx, parent_text in enumerate(parent_chunks):
            parent_id = f"{document_id}::parent::{parent_idx}"

            # Create child chunks from parent
            child_chunks = self._split_into_chunks(
                parent_text,
                self.child_chunk_size,
                self.overlap // 2
            )

            child_ids = []
            for child_idx, child_text in enumerate(child_chunks):
                child_id = f"{document_id}::child::{parent_idx}::{child_idx}"
                child_ids.append(child_id)

                chunks.append(ParentChildChunk(
                    id=child_id,
                    text=child_text,
                    parent_id=parent_id,
                    children_ids=[],
                    level=2,
                    metadata={
                        **metadata,
                        "document_id": document_id,
                        "parent_idx": parent_idx,
                        "child_idx": child_idx,
                        "char_start": self._calculate_char_start(
                            document_text, parent_chunks, parent_idx,
                            child_chunks, child_idx
                        )
                    }
                ))

            # Create parent chunk
            chunks.append(ParentChildChunk(
                id=parent_id,
                text=parent_text,
                parent_id=None,
                children_ids=child_ids,
                level=1,
                metadata={
                    **metadata,
                    "document_id": document_id,
                    "parent_idx": parent_idx,
                    "is_parent": True
                }
            ))

        return chunks

    def _split_into_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if not text or chunk_size <= 0:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end near chunk boundary
                search_start = max(start + chunk_size - 100, start)
                search_text = text[search_start:end + 100]
                sentence_end = self._find_sentence_boundary(search_text)
                if sentence_end > 0:
                    end = search_start + sentence_end

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end < len(text) else len(text)

        return chunks

    def _find_sentence_boundary(self, text: str) -> int:
        """Find a good sentence boundary in text."""
        # Look for period, question mark, or exclamation followed by space/newline
        matches = list(re.finditer(r'[.!?]\s', text))
        if matches:
            # Return position after the punctuation
            return matches[-1].end()
        return -1

    def _calculate_char_start(
        self,
        full_text: str,
        parent_chunks: List[str],
        parent_idx: int,
        child_chunks: List[str],
        child_idx: int
    ) -> int:
        """Calculate character start position for a child chunk."""
        # Approximate - for accurate positions, track during chunking
        parent_start = sum(len(p) for p in parent_chunks[:parent_idx])
        child_start = sum(len(c) for c in child_chunks[:child_idx])
        return parent_start + child_start

    def expand_to_parents(
        self,
        child_chunks: List[Dict[str, Any]],
        all_chunks: Dict[str, Dict[str, Any]]
    ) -> HierarchicalResult:
        """
        Expand child chunk results to include parent context.

        Args:
            child_chunks: Retrieved child chunks
            all_chunks: Map of all chunks by ID

        Returns:
            HierarchicalResult with expanded context
        """
        seen_parents = set()
        parent_chunks = []

        for chunk in child_chunks:
            parent_id = chunk.get("metadata", {}).get("parent_id") or chunk.get("parent_id")
            if parent_id and parent_id not in seen_parents:
                if parent_id in all_chunks:
                    parent_chunks.append(all_chunks[parent_id])
                    seen_parents.add(parent_id)

        return HierarchicalResult(
            chunks=child_chunks,
            parent_chunks=parent_chunks,
            context_expanded=bool(parent_chunks),
            expansion_strategy="child_to_parent"
        )

    def build_expanded_context(
        self,
        result: HierarchicalResult,
        include_children: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build final context from hierarchical result.

        Args:
            result: HierarchicalResult
            include_children: Whether to include child text in output

        Returns:
            List of chunks with expanded context
        """
        if not result.parent_chunks:
            return result.chunks

        expanded = []
        for parent in result.parent_chunks:
            expanded_chunk = {
                "id": parent.get("id"),
                "text": parent.get("text"),
                "score": max(
                    (c.get("score", 0) for c in result.chunks
                     if c.get("parent_id") == parent.get("id")),
                    default=0
                ),
                "is_expanded": True,
                "child_count": len([
                    c for c in result.chunks
                    if c.get("parent_id") == parent.get("id")
                ])
            }
            expanded.append(expanded_chunk)

        return expanded


def create_parent_child_index(
    documents: List[Dict[str, Any]],
    parent_size: int = 2000,
    child_size: int = 500
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Create parent-child chunk index from documents.

    Args:
        documents: List of documents with 'id', 'text', and optional 'metadata'
        parent_size: Size of parent chunks
        child_size: Size of child chunks

    Returns:
        Tuple of (all_chunks, child_to_parent_map)
    """
    retriever = ParentChildRetriever(
        parent_chunk_size=parent_size,
        child_chunk_size=child_size
    )

    all_chunks = []
    child_to_parent = {}

    for doc in documents:
        doc_id = doc.get("id", str(len(all_chunks)))
        doc_text = doc.get("text", "")
        doc_meta = doc.get("metadata", {})

        hierarchy = retriever.create_hierarchy(doc_text, doc_id, doc_meta)

        for chunk in hierarchy:
            chunk_dict = {
                "id": chunk.id,
                "text": chunk.text,
                "level": chunk.level,
                "parent_id": chunk.parent_id,
                "children_ids": chunk.children_ids,
                "metadata": chunk.metadata
            }
            all_chunks.append(chunk_dict)

            if chunk.parent_id:
                child_to_parent[chunk.id] = chunk.parent_id

    return all_chunks, child_to_parent


def expand_results_with_parents(
    search_results: List[Dict[str, Any]],
    child_to_parent: Dict[str, str],
    parent_chunks: Dict[str, Dict[str, Any]],
    max_parents: int = 3
) -> List[Dict[str, Any]]:
    """
    Expand search results to include parent chunks.

    Args:
        search_results: Retrieved chunks
        child_to_parent: Map from child ID to parent ID
        parent_chunks: Map of parent chunks by ID
        max_parents: Maximum number of parent chunks to include

    Returns:
        Expanded results with parent context
    """
    seen_parents = set()
    expanded = []

    for result in search_results:
        chunk_id = result.get("id", "")
        parent_id = child_to_parent.get(chunk_id)

        if parent_id and parent_id not in seen_parents and len(seen_parents) < max_parents:
            if parent_id in parent_chunks:
                parent = parent_chunks[parent_id].copy()
                parent["score"] = result.get("score", 0) * 0.9  # Slightly lower score
                parent["expanded_from"] = chunk_id
                expanded.append(parent)
                seen_parents.add(parent_id)

    # Combine with original results, parents first
    return expanded + search_results
