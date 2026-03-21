# src/ingestion/quality_validator.py
"""Pre-ingestion quality validation for documents."""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """A quality issue found in a document."""
    issue_type: str
    severity: str  # error, warning, info
    message: str
    location: Optional[str] = None


@dataclass
class QualityReport:
    """Quality validation report for a document."""
    file_path: str
    is_valid: bool
    quality_score: float  # 0-1
    issues: List[QualityIssue]
    stats: Dict[str, Any]


class QualityValidator:
    """
    Validates document quality before ingestion.

    Checks:
    - Minimum content length
    - Character encoding issues
    - Excessive whitespace/formatting
    - Language detection (optional)
    - Content coherence indicators
    """

    def __init__(
        self,
        min_content_length: int = 100,
        max_whitespace_ratio: float = 0.5,
        min_word_count: int = 20,
        min_avg_word_length: float = 2.0,
        max_avg_word_length: float = 20.0
    ):
        self.min_content_length = min_content_length
        self.max_whitespace_ratio = max_whitespace_ratio
        self.min_word_count = min_word_count
        self.min_avg_word_length = min_avg_word_length
        self.max_avg_word_length = max_avg_word_length

    def validate(self, content: str, file_path: str = "") -> QualityReport:
        """
        Validate document content quality.

        Args:
            content: Document text content
            file_path: Path to the document (for reporting)

        Returns:
            QualityReport with validation results
        """
        issues = []
        stats = {}

        if not content:
            return QualityReport(
                file_path=file_path,
                is_valid=False,
                quality_score=0.0,
                issues=[QualityIssue(
                    issue_type="empty_content",
                    severity="error",
                    message="Document has no content"
                )],
                stats={"char_count": 0}
            )

        # Basic stats
        char_count = len(content)
        word_count = len(content.split())
        line_count = content.count('\n') + 1
        whitespace_count = sum(1 for c in content if c.isspace())

        stats = {
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "whitespace_ratio": whitespace_count / char_count if char_count else 0
        }

        # Check minimum length
        if char_count < self.min_content_length:
            issues.append(QualityIssue(
                issue_type="too_short",
                severity="error",
                message=f"Content too short ({char_count} chars, min {self.min_content_length})"
            ))

        # Check minimum word count
        if word_count < self.min_word_count:
            issues.append(QualityIssue(
                issue_type="too_few_words",
                severity="warning",
                message=f"Too few words ({word_count}, min {self.min_word_count})"
            ))

        # Check whitespace ratio
        whitespace_ratio = stats["whitespace_ratio"]
        if whitespace_ratio > self.max_whitespace_ratio:
            issues.append(QualityIssue(
                issue_type="excessive_whitespace",
                severity="warning",
                message=f"Excessive whitespace ({whitespace_ratio:.1%})"
            ))

        # Check average word length (indicates garbage/encoding issues)
        if word_count > 0:
            words = content.split()
            avg_word_length = sum(len(w) for w in words) / len(words)
            stats["avg_word_length"] = avg_word_length

            if avg_word_length < self.min_avg_word_length:
                issues.append(QualityIssue(
                    issue_type="short_words",
                    severity="warning",
                    message=f"Very short average word length ({avg_word_length:.1f})"
                ))
            elif avg_word_length > self.max_avg_word_length:
                issues.append(QualityIssue(
                    issue_type="long_words",
                    severity="warning",
                    message=f"Very long average word length ({avg_word_length:.1f}) - possible encoding issue"
                ))

        # Check for encoding issues (high ratio of replacement chars)
        replacement_chars = content.count('\ufffd') + content.count('�')
        if replacement_chars > 0:
            ratio = replacement_chars / char_count
            stats["replacement_char_ratio"] = ratio
            if ratio > 0.01:
                issues.append(QualityIssue(
                    issue_type="encoding_issues",
                    severity="warning",
                    message=f"Possible encoding issues ({replacement_chars} replacement characters)"
                ))

        # Check for excessive repetition
        repetition_score = self._check_repetition(content)
        stats["repetition_score"] = repetition_score
        if repetition_score > 0.5:
            issues.append(QualityIssue(
                issue_type="high_repetition",
                severity="warning",
                message=f"High content repetition detected ({repetition_score:.1%})"
            ))

        # Check for mostly non-alphabetic content
        alpha_ratio = sum(1 for c in content if c.isalpha()) / char_count if char_count else 0
        stats["alpha_ratio"] = alpha_ratio
        if alpha_ratio < 0.3:
            issues.append(QualityIssue(
                issue_type="low_text_content",
                severity="warning",
                message=f"Low alphabetic content ({alpha_ratio:.1%}) - may be data/code"
            ))

        # Calculate quality score
        quality_score = self._calculate_score(issues, stats)

        # Determine validity
        has_errors = any(i.severity == "error" for i in issues)
        is_valid = not has_errors and quality_score >= 0.3

        return QualityReport(
            file_path=file_path,
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            stats=stats
        )

    def _check_repetition(self, content: str, ngram_size: int = 5) -> float:
        """Check for repetitive content using n-gram analysis."""
        words = content.lower().split()
        if len(words) < ngram_size * 2:
            return 0.0

        ngrams = []
        for i in range(len(words) - ngram_size + 1):
            ngram = tuple(words[i:i + ngram_size])
            ngrams.append(ngram)

        if not ngrams:
            return 0.0

        unique_ngrams = len(set(ngrams))
        total_ngrams = len(ngrams)

        # Repetition score: 1 - (unique / total)
        return 1 - (unique_ngrams / total_ngrams)

    def _calculate_score(
        self,
        issues: List[QualityIssue],
        stats: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score."""
        score = 1.0

        # Deduct for issues
        for issue in issues:
            if issue.severity == "error":
                score -= 0.4
            elif issue.severity == "warning":
                score -= 0.15
            else:
                score -= 0.05

        # Bonus for good stats
        if stats.get("alpha_ratio", 0) > 0.7:
            score += 0.1
        if stats.get("repetition_score", 1) < 0.2:
            score += 0.1

        return max(0.0, min(1.0, score))

    def validate_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[QualityReport]:
        """
        Validate a batch of documents.

        Args:
            documents: List of dicts with 'path' and 'content' keys

        Returns:
            List of QualityReport for each document
        """
        reports = []
        for doc in documents:
            path = doc.get("path", doc.get("file_path", ""))
            content = doc.get("content", doc.get("text", ""))
            reports.append(self.validate(content, path))
        return reports


# Module-level singleton
_validator = None


def get_quality_validator() -> QualityValidator:
    """Get singleton quality validator instance."""
    global _validator
    if _validator is None:
        _validator = QualityValidator()
    return _validator


def validate_document(content: str, file_path: str = "") -> QualityReport:
    """Validate a document (convenience function)."""
    return get_quality_validator().validate(content, file_path)


def validate_documents(documents: List[Dict[str, Any]]) -> List[QualityReport]:
    """Validate a batch of documents (convenience function)."""
    return get_quality_validator().validate_batch(documents)
