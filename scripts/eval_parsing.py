#!/usr/bin/env python3
"""
Automated parsing quality evaluation.

Usage:
    python scripts/eval_parsing.py tests/eval_data/documents

Measures:
- Element extraction counts
- Structure preservation (tables, headings)
- Format coverage
"""

import sys
import json
from pathlib import Path
from collections import Counter
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.docling_loader import (
    load_documents_with_docling,
    SUPPORTED_EXTENSIONS
)


@dataclass
class ParsingMetrics:
    """Metrics for parsing quality evaluation."""
    total_documents: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    total_elements: int = 0
    total_chars: int = 0
    elements_by_type: Dict[str, int] = None
    formats_processed: Dict[str, int] = None
    avg_elements_per_doc: float = 0.0
    avg_chars_per_doc: float = 0.0
    documents_with_tables: int = 0
    documents_with_headings: int = 0
    issues: List[str] = None

    def __post_init__(self):
        if self.elements_by_type is None:
            self.elements_by_type = {}
        if self.formats_processed is None:
            self.formats_processed = {}
        if self.issues is None:
            self.issues = []


def evaluate_parsing(docs_dir: str) -> ParsingMetrics:
    """Evaluate parsing quality across all documents in directory."""

    docs = load_documents_with_docling(docs_dir, recursive=True)

    metrics = ParsingMetrics()
    metrics.total_documents = len(docs)

    element_types = Counter()
    format_counts = Counter()

    for doc in docs:
        format_counts[doc.format] += 1

        if doc.status != "OK":
            metrics.failed_documents += 1
            metrics.issues.append(f"{doc.filename}: {doc.status} - {doc.error}")
            continue

        metrics.successful_documents += 1
        metrics.total_elements += len(doc.elements)
        metrics.total_chars += doc.chars

        # Count element types
        doc_types = Counter(el.element_type for el in doc.elements)
        element_types.update(doc_types)

        # Check for tables and headings
        if doc_types.get("table", 0) > 0:
            metrics.documents_with_tables += 1
        if doc_types.get("heading", 0) > 0:
            metrics.documents_with_headings += 1

        # Check for potential issues
        if len(doc.elements) == 0:
            metrics.issues.append(f"{doc.filename}: No elements extracted")
        elif len(doc.elements) < 3:
            metrics.issues.append(f"{doc.filename}: Very few elements ({len(doc.elements)})")

    # Calculate averages
    if metrics.successful_documents > 0:
        metrics.avg_elements_per_doc = metrics.total_elements / metrics.successful_documents
        metrics.avg_chars_per_doc = metrics.total_chars / metrics.successful_documents

    metrics.elements_by_type = dict(element_types)
    metrics.formats_processed = dict(format_counts)

    return metrics


def print_report(metrics: ParsingMetrics):
    """Print evaluation report."""

    print("\n" + "=" * 60)
    print("  PARSING QUALITY EVALUATION REPORT")
    print("=" * 60)

    # Document stats
    print("\n📄 Document Statistics")
    print(f"  Total documents: {metrics.total_documents}")
    print(f"  Successful: {metrics.successful_documents}")
    print(f"  Failed: {metrics.failed_documents}")

    success_rate = (metrics.successful_documents / metrics.total_documents * 100
                   if metrics.total_documents > 0 else 0)
    print(f"  Success rate: {success_rate:.1f}%")

    # Format breakdown
    print("\n📁 Formats Processed")
    for fmt, count in sorted(metrics.formats_processed.items()):
        print(f"  {fmt}: {count}")

    # Element stats
    print("\n🔢 Element Statistics")
    print(f"  Total elements: {metrics.total_elements}")
    print(f"  Total characters: {metrics.total_chars:,}")
    print(f"  Avg elements/doc: {metrics.avg_elements_per_doc:.1f}")
    print(f"  Avg chars/doc: {metrics.avg_chars_per_doc:,.0f}")

    # Element types
    print("\n📊 Element Types")
    for el_type, count in sorted(metrics.elements_by_type.items(), key=lambda x: -x[1]):
        print(f"  {el_type}: {count}")

    # Structure detection
    print("\n🏗️ Structure Detection")
    print(f"  Documents with tables: {metrics.documents_with_tables}")
    print(f"  Documents with headings: {metrics.documents_with_headings}")

    # Issues
    if metrics.issues:
        print("\n⚠️ Issues Found")
        for issue in metrics.issues[:10]:
            print(f"  - {issue}")
        if len(metrics.issues) > 10:
            print(f"  ... and {len(metrics.issues) - 10} more")
    else:
        print("\n✅ No issues detected")

    # Quality score
    print("\n📈 Quality Score")
    score = calculate_quality_score(metrics)
    print(f"  Overall: {score:.0f}/100")

    return score


def calculate_quality_score(metrics: ParsingMetrics) -> float:
    """Calculate overall quality score (0-100)."""

    if metrics.total_documents == 0:
        return 0.0

    score = 0.0

    # Success rate (40 points max)
    success_rate = metrics.successful_documents / metrics.total_documents
    score += success_rate * 40

    # Element extraction (30 points max)
    if metrics.avg_elements_per_doc > 10:
        score += 30
    elif metrics.avg_elements_per_doc > 5:
        score += 20
    elif metrics.avg_elements_per_doc > 1:
        score += 10

    # Structure detection (20 points max)
    if metrics.successful_documents > 0:
        table_rate = metrics.documents_with_tables / metrics.successful_documents
        heading_rate = metrics.documents_with_headings / metrics.successful_documents
        score += (table_rate + heading_rate) * 10

    # No issues bonus (10 points)
    if len(metrics.issues) == 0:
        score += 10

    return min(score, 100)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/eval_parsing.py /path/to/documents")
        sys.exit(1)

    docs_dir = sys.argv[1]

    if not Path(docs_dir).is_dir():
        print(f"Error: Directory not found: {docs_dir}")
        sys.exit(1)

    metrics = evaluate_parsing(docs_dir)
    score = print_report(metrics)

    # Output JSON if requested
    if "--json" in sys.argv:
        print("\n" + json.dumps(asdict(metrics), indent=2))

    # Exit with error if score is too low
    if score < 50:
        sys.exit(1)
