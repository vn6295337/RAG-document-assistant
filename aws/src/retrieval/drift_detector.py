# src/retrieval/drift_detector.py
"""Embedding drift detection for monitoring embedding quality over time."""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class DriftMetrics:
    """Metrics for embedding drift detection."""
    timestamp: str
    sample_size: int
    mean_similarity: float
    std_similarity: float
    min_similarity: float
    max_similarity: float
    below_threshold_count: int
    drift_detected: bool
    drift_severity: str  # none, low, medium, high


@dataclass
class DriftReport:
    """Complete drift detection report."""
    current_metrics: DriftMetrics
    baseline_metrics: Optional[DriftMetrics]
    drift_score: float  # 0-1, higher = more drift
    recommendations: List[str]


# Reference queries for drift detection
REFERENCE_QUERIES = [
    "What is the main topic of this document?",
    "Summarize the key points",
    "What are the conclusions?",
    "List the important dates or deadlines",
    "Who are the main stakeholders mentioned?",
]


class EmbeddingDriftDetector:
    """
    Detects embedding drift by comparing current embeddings
    to historical baselines.

    Drift can occur when:
    - Embedding model changes
    - Document corpus significantly changes
    - Index becomes stale or corrupted
    """

    def __init__(
        self,
        similarity_threshold: float = 0.5,
        drift_threshold: float = 0.15,
        baseline_path: str = None
    ):
        self.similarity_threshold = similarity_threshold
        self.drift_threshold = drift_threshold
        self.baseline_path = baseline_path or os.getenv(
            "DRIFT_BASELINE_PATH",
            "/tmp/drift_baseline.json"
        )
        self._baseline: Optional[DriftMetrics] = None

    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def measure_query_chunk_similarity(
        self,
        query_embeddings: List[List[float]],
        chunk_embeddings: List[List[float]]
    ) -> DriftMetrics:
        """
        Measure similarity distribution between queries and retrieved chunks.

        Args:
            query_embeddings: List of query embedding vectors
            chunk_embeddings: List of corresponding chunk embeddings

        Returns:
            DriftMetrics with similarity statistics
        """
        if not query_embeddings or not chunk_embeddings:
            return DriftMetrics(
                timestamp=datetime.utcnow().isoformat(),
                sample_size=0,
                mean_similarity=0.0,
                std_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                below_threshold_count=0,
                drift_detected=False,
                drift_severity="none"
            )

        similarities = []
        for q_emb, c_emb in zip(query_embeddings, chunk_embeddings):
            sim = self.compute_similarity(q_emb, c_emb)
            similarities.append(sim)

        below_threshold = sum(1 for s in similarities if s < self.similarity_threshold)

        mean_sim = statistics.mean(similarities) if similarities else 0.0
        std_sim = statistics.stdev(similarities) if len(similarities) > 1 else 0.0

        # Detect drift based on mean similarity drop
        drift_detected = mean_sim < (1 - self.drift_threshold)
        drift_severity = self._calculate_severity(mean_sim)

        return DriftMetrics(
            timestamp=datetime.utcnow().isoformat(),
            sample_size=len(similarities),
            mean_similarity=round(mean_sim, 4),
            std_similarity=round(std_sim, 4),
            min_similarity=round(min(similarities), 4) if similarities else 0.0,
            max_similarity=round(max(similarities), 4) if similarities else 0.0,
            below_threshold_count=below_threshold,
            drift_detected=drift_detected,
            drift_severity=drift_severity
        )

    def _calculate_severity(self, mean_similarity: float) -> str:
        """Calculate drift severity based on mean similarity."""
        if mean_similarity >= 0.7:
            return "none"
        elif mean_similarity >= 0.5:
            return "low"
        elif mean_similarity >= 0.3:
            return "medium"
        else:
            return "high"

    def load_baseline(self) -> Optional[DriftMetrics]:
        """Load baseline metrics from storage."""
        if self._baseline:
            return self._baseline

        try:
            if os.path.exists(self.baseline_path):
                with open(self.baseline_path, "r") as f:
                    data = json.load(f)
                    self._baseline = DriftMetrics(**data)
                    return self._baseline
        except Exception as e:
            logger.warning(f"Failed to load drift baseline: {e}")

        return None

    def save_baseline(self, metrics: DriftMetrics) -> bool:
        """Save current metrics as new baseline."""
        try:
            with open(self.baseline_path, "w") as f:
                json.dump(asdict(metrics), f, indent=2)
            self._baseline = metrics
            return True
        except Exception as e:
            logger.error(f"Failed to save drift baseline: {e}")
            return False

    def detect_drift(
        self,
        current_metrics: DriftMetrics
    ) -> DriftReport:
        """
        Compare current metrics against baseline to detect drift.

        Args:
            current_metrics: Current embedding similarity metrics

        Returns:
            DriftReport with drift analysis
        """
        baseline = self.load_baseline()
        recommendations = []

        if not baseline:
            # No baseline - save current as baseline
            self.save_baseline(current_metrics)
            return DriftReport(
                current_metrics=current_metrics,
                baseline_metrics=None,
                drift_score=0.0,
                recommendations=["Baseline established. Future comparisons will use this."]
            )

        # Calculate drift score
        drift_score = self._calculate_drift_score(baseline, current_metrics)

        # Generate recommendations
        if drift_score > 0.3:
            recommendations.append("High drift detected. Consider re-indexing documents.")
        if current_metrics.below_threshold_count > baseline.below_threshold_count * 1.5:
            recommendations.append("Significant increase in low-similarity results. Check embedding model consistency.")
        if current_metrics.std_similarity > baseline.std_similarity * 1.5:
            recommendations.append("Increased variance in similarities. Document corpus may have changed significantly.")
        if current_metrics.drift_severity in ["medium", "high"]:
            recommendations.append(f"Drift severity: {current_metrics.drift_severity}. Review recent changes.")

        if not recommendations:
            recommendations.append("Embeddings appear stable. No action needed.")

        return DriftReport(
            current_metrics=current_metrics,
            baseline_metrics=baseline,
            drift_score=round(drift_score, 4),
            recommendations=recommendations
        )

    def _calculate_drift_score(
        self,
        baseline: DriftMetrics,
        current: DriftMetrics
    ) -> float:
        """Calculate overall drift score (0-1)."""
        if baseline.mean_similarity == 0:
            return 0.0

        # Components of drift score
        mean_drift = abs(baseline.mean_similarity - current.mean_similarity)
        std_drift = abs(baseline.std_similarity - current.std_similarity) if baseline.std_similarity > 0 else 0

        # Weighted combination
        drift_score = 0.7 * mean_drift + 0.3 * std_drift

        return min(1.0, drift_score)


# Module-level singleton
_detector = None


def get_drift_detector() -> EmbeddingDriftDetector:
    """Get singleton drift detector instance."""
    global _detector
    if _detector is None:
        _detector = EmbeddingDriftDetector()
    return _detector


async def run_drift_check(
    search_fn,
    embedding_fn,
    queries: List[str] = None
) -> DriftReport:
    """
    Run drift detection using provided search and embedding functions.

    Args:
        search_fn: Function to search for chunks (async)
        embedding_fn: Function to generate embeddings
        queries: Optional custom queries (uses defaults if None)

    Returns:
        DriftReport with drift analysis
    """
    detector = get_drift_detector()
    test_queries = queries or REFERENCE_QUERIES

    query_embeddings = []
    chunk_embeddings = []

    for query in test_queries:
        try:
            # Get query embedding
            q_emb = embedding_fn(query)
            if not q_emb:
                continue

            # Search for relevant chunks
            results = await search_fn(query)
            if not results:
                continue

            # Get top chunk's embedding (from Pinecone metadata or re-embed)
            top_chunk = results[0] if results else None
            if top_chunk:
                chunk_text = top_chunk.get("text", "")
                if chunk_text:
                    c_emb = embedding_fn(chunk_text)
                    if c_emb:
                        query_embeddings.append(q_emb)
                        chunk_embeddings.append(c_emb)

        except Exception as e:
            logger.warning(f"Drift check query failed: {e}")
            continue

    metrics = detector.measure_query_chunk_similarity(query_embeddings, chunk_embeddings)
    return detector.detect_drift(metrics)


def check_drift_sync(
    query_embeddings: List[List[float]],
    chunk_embeddings: List[List[float]]
) -> DriftReport:
    """
    Synchronous drift check with pre-computed embeddings.

    Args:
        query_embeddings: Pre-computed query embeddings
        chunk_embeddings: Pre-computed chunk embeddings

    Returns:
        DriftReport
    """
    detector = get_drift_detector()
    metrics = detector.measure_query_chunk_similarity(query_embeddings, chunk_embeddings)
    return detector.detect_drift(metrics)
