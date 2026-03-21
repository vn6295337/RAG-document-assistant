# src/context/sentence_pruner.py
"""Sentence-level pruning for context optimization."""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SentenceScore:
    """Scored sentence with metadata."""
    text: str
    score: float
    position: int  # Original position in chunk
    chunk_id: str
    relevance_signals: List[str]


@dataclass
class PruningResult:
    """Result of sentence pruning."""
    original_text: str
    pruned_text: str
    original_sentences: int
    retained_sentences: int
    removed_sentences: int
    compression_ratio: float
    retained_scores: List[float]


class SentencePruner:
    """
    Prunes irrelevant sentences from chunks to optimize context.

    Uses multiple signals:
    - Query term overlap
    - Position (first/last sentences often important)
    - Sentence length (very short often uninformative)
    - Semantic markers (e.g., "importantly", "in conclusion")
    """

    def __init__(
        self,
        min_sentence_length: int = 20,
        max_sentence_length: int = 500,
        position_boost: float = 0.1,
        min_score_threshold: float = 0.1
    ):
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        self.position_boost = position_boost
        self.min_score_threshold = min_score_threshold

        # Importance markers
        self.importance_markers = [
            r'\b(important|crucial|key|essential|significant|notably)\b',
            r'\b(in conclusion|to summarize|in summary|therefore|thus|hence)\b',
            r'\b(first|second|third|finally|lastly)\b',
            r'\b(must|should|need to|required|necessary)\b',
            r'\b(because|since|due to|as a result)\b',
        ]

        # Low-value patterns
        self.low_value_patterns = [
            r'^(however|moreover|furthermore|additionally),?\s*$',
            r'^(see|refer to|as mentioned)\b',
            r'^\s*\d+\.\s*$',  # Just a number
            r'^(note:|nb:|fyi:)',
        ]

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        if not text:
            return []

        # Handle common abbreviations to avoid false splits
        text = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|etc|vs|e\.g|i\.e)\.', r'\1<DOT>', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Restore dots
        sentences = [s.replace('<DOT>', '.').strip() for s in sentences]

        # Filter empty
        return [s for s in sentences if s]

    def score_sentence(
        self,
        sentence: str,
        query_terms: List[str],
        position: int,
        total_sentences: int,
        chunk_id: str = ""
    ) -> SentenceScore:
        """
        Score a sentence for relevance.

        Args:
            sentence: The sentence text
            query_terms: List of query terms to match
            position: Position in the chunk (0-indexed)
            total_sentences: Total sentences in chunk
            chunk_id: ID of the source chunk

        Returns:
            SentenceScore with relevance score
        """
        score = 0.0
        signals = []
        sentence_lower = sentence.lower()

        # 1. Query term overlap
        term_matches = 0
        for term in query_terms:
            if term.lower() in sentence_lower:
                term_matches += 1

        if query_terms:
            term_score = term_matches / len(query_terms)
            score += term_score * 0.5
            if term_matches > 0:
                signals.append(f"query_match:{term_matches}")

        # 2. Position boost (first and last sentences)
        if position == 0:
            score += self.position_boost
            signals.append("first_sentence")
        elif position == total_sentences - 1:
            score += self.position_boost * 0.5
            signals.append("last_sentence")

        # 3. Importance markers
        for pattern in self.importance_markers:
            if re.search(pattern, sentence_lower):
                score += 0.15
                signals.append("importance_marker")
                break

        # 4. Length penalty for very short sentences
        if len(sentence) < self.min_sentence_length:
            score *= 0.5
            signals.append("too_short")
        elif len(sentence) > self.max_sentence_length:
            score *= 0.8
            signals.append("very_long")

        # 5. Low-value pattern penalty
        for pattern in self.low_value_patterns:
            if re.search(pattern, sentence_lower):
                score *= 0.3
                signals.append("low_value")
                break

        # 6. Contains numbers/data (often informative)
        if re.search(r'\d+(?:\.\d+)?%?', sentence):
            score += 0.1
            signals.append("has_data")

        # 7. Contains proper nouns (entities)
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence):
            score += 0.05
            signals.append("has_entities")

        return SentenceScore(
            text=sentence,
            score=min(1.0, score),
            position=position,
            chunk_id=chunk_id,
            relevance_signals=signals
        )

    def prune_chunk(
        self,
        chunk_text: str,
        query: str,
        target_ratio: float = 0.7,
        chunk_id: str = ""
    ) -> PruningResult:
        """
        Prune a chunk by removing low-relevance sentences.

        Args:
            chunk_text: Original chunk text
            query: User query for relevance scoring
            target_ratio: Target retention ratio (0-1)
            chunk_id: Chunk identifier

        Returns:
            PruningResult with pruned text
        """
        sentences = self.split_sentences(chunk_text)

        if not sentences:
            return PruningResult(
                original_text=chunk_text,
                pruned_text=chunk_text,
                original_sentences=0,
                retained_sentences=0,
                removed_sentences=0,
                compression_ratio=1.0,
                retained_scores=[]
            )

        # Extract query terms
        query_terms = self._extract_terms(query)

        # Score all sentences
        scored = []
        for i, sent in enumerate(sentences):
            score = self.score_sentence(
                sent, query_terms, i, len(sentences), chunk_id
            )
            scored.append(score)

        # Determine how many to keep
        target_count = max(1, int(len(sentences) * target_ratio))

        # Sort by score, but preserve some position weighting
        # (don't completely reorder)
        scored_with_position = [
            (s.score + (0.01 * (len(sentences) - s.position)), s)
            for s in scored
        ]
        scored_with_position.sort(key=lambda x: x[0], reverse=True)

        # Select top sentences
        retained = scored_with_position[:target_count]
        retained_scores = [s for _, s in retained]

        # Sort by original position for coherent output
        retained_scores.sort(key=lambda x: x.position)

        # Build pruned text
        pruned_text = " ".join(s.text for s in retained_scores)

        return PruningResult(
            original_text=chunk_text,
            pruned_text=pruned_text,
            original_sentences=len(sentences),
            retained_sentences=len(retained_scores),
            removed_sentences=len(sentences) - len(retained_scores),
            compression_ratio=len(pruned_text) / len(chunk_text) if chunk_text else 1.0,
            retained_scores=[s.score for s in retained_scores]
        )

    def prune_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        target_ratio: float = 0.7,
        min_chunk_length: int = 100
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Prune multiple chunks.

        Args:
            chunks: List of chunks with 'text' and 'id' fields
            query: User query
            target_ratio: Target retention ratio
            min_chunk_length: Don't prune chunks shorter than this

        Returns:
            Tuple of (pruned_chunks, pruning_stats)
        """
        pruned_chunks = []
        total_original = 0
        total_pruned = 0
        chunks_pruned = 0

        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_id = chunk.get("id", "")

            total_original += len(chunk_text)

            # Skip short chunks
            if len(chunk_text) < min_chunk_length:
                pruned_chunks.append(chunk)
                total_pruned += len(chunk_text)
                continue

            result = self.prune_chunk(chunk_text, query, target_ratio, chunk_id)

            pruned_chunk = chunk.copy()
            pruned_chunk["text"] = result.pruned_text
            pruned_chunk["pruning"] = {
                "original_sentences": result.original_sentences,
                "retained_sentences": result.retained_sentences,
                "compression_ratio": round(result.compression_ratio, 2)
            }
            pruned_chunks.append(pruned_chunk)

            total_pruned += len(result.pruned_text)
            if result.removed_sentences > 0:
                chunks_pruned += 1

        stats = {
            "chunks_processed": len(chunks),
            "chunks_pruned": chunks_pruned,
            "original_chars": total_original,
            "pruned_chars": total_pruned,
            "overall_compression": round(total_pruned / total_original, 2) if total_original else 1.0
        }

        return pruned_chunks, stats

    def _extract_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from query."""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some",
            "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "just", "and", "but", "if", "or",
            "because", "until", "while", "what", "which", "who", "whom",
            "this", "that", "these", "those", "am", "it", "its", "i", "me",
            "my", "myself", "we", "our", "ours", "ourselves", "you", "your"
        }

        words = re.findall(r'\b[a-zA-Z]{2,}\b', query.lower())
        return [w for w in words if w not in stop_words]


# Module-level singleton
_pruner = None


def get_sentence_pruner() -> SentencePruner:
    """Get singleton sentence pruner instance."""
    global _pruner
    if _pruner is None:
        _pruner = SentencePruner()
    return _pruner


def prune_chunk(
    chunk_text: str,
    query: str,
    target_ratio: float = 0.7
) -> PruningResult:
    """Prune a single chunk (convenience function)."""
    return get_sentence_pruner().prune_chunk(chunk_text, query, target_ratio)


def prune_chunks(
    chunks: List[Dict[str, Any]],
    query: str,
    target_ratio: float = 0.7
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Prune multiple chunks (convenience function)."""
    return get_sentence_pruner().prune_chunks(chunks, query, target_ratio)
