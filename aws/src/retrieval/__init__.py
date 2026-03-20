# Enhanced retrieval for AWS track
from src.retrieval.hyde import (
    HyDEResult,
    generate_hypothetical_document,
    hyde_search
)
from src.retrieval.llm_reranker import (
    LLMRerankResult,
    llm_rerank,
    hybrid_rerank
)
from src.retrieval.drift_detector import (
    DriftMetrics,
    DriftReport,
    EmbeddingDriftDetector,
    get_drift_detector,
    run_drift_check,
    check_drift_sync
)
from src.retrieval.parent_child import (
    ParentChildChunk,
    HierarchicalResult,
    ParentChildRetriever,
    create_parent_child_index,
    expand_results_with_parents
)
from src.retrieval.stale_detector import (
    DocumentReference,
    StaleCheckResult,
    StaleReport,
    StaleReferenceDetector,
    get_stale_detector,
    register_indexed_document,
    check_for_stale_references
)
from src.retrieval.index_cleanup import (
    IndexCleaner,
    IndexStats,
    CleanupResult,
    get_index_cleaner,
    get_index_stats,
    cleanup_deleted_files,
    delete_vectors
)
from src.retrieval.embedding_versioning import (
    EmbeddingModelVersion,
    MigrationPlan,
    MigrationStatus,
    EmbeddingVersionManager,
    get_version_manager,
    register_embedding_version,
    get_active_embedding_version,
    plan_embedding_migration
)

__all__ = [
    # HyDE
    "HyDEResult",
    "generate_hypothetical_document",
    "hyde_search",
    # LLM Reranker
    "LLMRerankResult",
    "llm_rerank",
    "hybrid_rerank",
    # Drift Detection
    "DriftMetrics",
    "DriftReport",
    "EmbeddingDriftDetector",
    "get_drift_detector",
    "run_drift_check",
    "check_drift_sync",
    # Parent-Child
    "ParentChildChunk",
    "HierarchicalResult",
    "ParentChildRetriever",
    "create_parent_child_index",
    "expand_results_with_parents",
    # Stale Detection
    "DocumentReference",
    "StaleCheckResult",
    "StaleReport",
    "StaleReferenceDetector",
    "get_stale_detector",
    "register_indexed_document",
    "check_for_stale_references",
    # Index Cleanup
    "IndexCleaner",
    "IndexStats",
    "CleanupResult",
    "get_index_cleaner",
    "get_index_stats",
    "cleanup_deleted_files",
    "delete_vectors",
    # Embedding Versioning
    "EmbeddingModelVersion",
    "MigrationPlan",
    "MigrationStatus",
    "EmbeddingVersionManager",
    "get_version_manager",
    "register_embedding_version",
    "get_active_embedding_version",
    "plan_embedding_migration"
]
