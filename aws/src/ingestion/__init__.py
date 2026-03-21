# Ingestion modules for AWS track
from src.ingestion.deduplicator import (
    DocumentDeduplicator,
    DeduplicationResult,
    get_deduplicator,
    check_duplicate,
    deduplicate_documents
)
from src.ingestion.quality_validator import (
    QualityValidator,
    QualityReport,
    QualityIssue,
    get_quality_validator,
    validate_document,
    validate_documents
)

__all__ = [
    # Deduplication
    "DocumentDeduplicator",
    "DeduplicationResult",
    "get_deduplicator",
    "check_duplicate",
    "deduplicate_documents",
    # Quality Validation
    "QualityValidator",
    "QualityReport",
    "QualityIssue",
    "get_quality_validator",
    "validate_document",
    "validate_documents"
]
