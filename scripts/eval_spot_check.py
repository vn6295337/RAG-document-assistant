#!/usr/bin/env python3
"""
Quick spot check for Docling parsing quality.

Usage:
    python scripts/eval_spot_check.py /path/to/documents
    python scripts/eval_spot_check.py /path/to/single/file.pdf

Outputs a visual summary of how Docling parsed each document.
"""

import sys
import os
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.docling_loader import (
    load_document_with_docling,
    load_documents_with_docling,
    SUPPORTED_EXTENSIONS,
    ParsedDocument
)


def print_header(text: str, char: str = "="):
    """Print a formatted header."""
    print(f"\n{char * 60}")
    print(f"  {text}")
    print(f"{char * 60}")


def analyze_document(doc: ParsedDocument, verbose: bool = True) -> dict:
    """Analyze a single parsed document and return metrics."""

    # Count elements by type
    type_counts = Counter(el.element_type for el in doc.elements)

    # Check for potential issues
    issues = []
    if doc.status != "OK":
        issues.append(f"Status: {doc.status} - {doc.error}")
    if len(doc.elements) == 0:
        issues.append("No elements extracted!")
    if doc.chars == 0:
        issues.append("Zero characters extracted!")
    if type_counts.get("table", 0) == 0 and doc.format == ".pdf":
        # PDFs often have tables - flag if none found
        issues.append("No tables detected (may be expected)")

    # Calculate metrics
    metrics = {
        "filename": doc.filename,
        "format": doc.format,
        "status": doc.status,
        "total_elements": len(doc.elements),
        "total_chars": doc.chars,
        "total_words": doc.words,
        "page_count": doc.page_count,
        "element_types": dict(type_counts),
        "issues": issues
    }

    if verbose:
        print_header(f"{doc.filename} ({doc.format})", "-")
        print(f"  Status: {doc.status}")
        print(f"  Elements: {len(doc.elements)}")
        print(f"  Characters: {doc.chars:,}")
        print(f"  Words: {doc.words:,}")
        if doc.page_count:
            print(f"  Pages: {doc.page_count}")

        print(f"\n  Element breakdown:")
        for el_type, count in sorted(type_counts.items()):
            print(f"    {el_type}: {count}")

        if issues:
            print(f"\n  ⚠️  Potential issues:")
            for issue in issues:
                print(f"    - {issue}")

        # Show sample elements
        print(f"\n  Sample elements (first 5):")
        for i, el in enumerate(doc.elements[:5]):
            text_preview = el.text[:80].replace('\n', ' ')
            if len(el.text) > 80:
                text_preview += "..."
            print(f"    [{el.element_type}] {text_preview}")

        # Show table preview if any
        tables = [el for el in doc.elements if el.element_type == "table"]
        if tables:
            print(f"\n  Table preview (first table):")
            table_text = tables[0].text[:300].replace('\n', '\n    ')
            print(f"    {table_text}")
            if len(tables[0].text) > 300:
                print("    ...")

    return metrics


def run_spot_check(path: str, verbose: bool = True):
    """Run spot check on a file or directory."""

    path = Path(path)

    print_header("DOCLING PARSING SPOT CHECK")
    print(f"  Path: {path}")
    print(f"  Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    all_metrics = []

    if path.is_file():
        # Single file
        doc = load_document_with_docling(str(path))
        metrics = analyze_document(doc, verbose=verbose)
        all_metrics.append(metrics)

    elif path.is_dir():
        # Directory
        docs = load_documents_with_docling(str(path), recursive=True)
        print(f"  Found {len(docs)} documents")

        for doc in docs:
            metrics = analyze_document(doc, verbose=verbose)
            all_metrics.append(metrics)

    else:
        print(f"  ERROR: Path not found: {path}")
        return []

    # Summary
    print_header("SUMMARY")

    ok_count = sum(1 for m in all_metrics if m["status"] == "OK")
    total_elements = sum(m["total_elements"] for m in all_metrics)
    total_chars = sum(m["total_chars"] for m in all_metrics)

    print(f"  Documents processed: {len(all_metrics)}")
    print(f"  Successful (OK): {ok_count}")
    print(f"  Failed/Skipped: {len(all_metrics) - ok_count}")
    print(f"  Total elements: {total_elements}")
    print(f"  Total characters: {total_chars:,}")

    # Aggregate element types
    all_types = Counter()
    for m in all_metrics:
        all_types.update(m["element_types"])

    print(f"\n  Element types across all docs:")
    for el_type, count in sorted(all_types.items(), key=lambda x: -x[1]):
        print(f"    {el_type}: {count}")

    # All issues
    all_issues = []
    for m in all_metrics:
        for issue in m["issues"]:
            all_issues.append(f"{m['filename']}: {issue}")

    if all_issues:
        print(f"\n  ⚠️  Issues found:")
        for issue in all_issues[:10]:
            print(f"    - {issue}")
        if len(all_issues) > 10:
            print(f"    ... and {len(all_issues) - 10} more")
    else:
        print(f"\n  ✅ No issues detected")

    return all_metrics


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/eval_spot_check.py /path/to/documents")
        print("\nExamples:")
        print("  python scripts/eval_spot_check.py ./tests/eval_data/documents")
        print("  python scripts/eval_spot_check.py ./report.pdf")
        sys.exit(1)

    target_path = sys.argv[1]
    verbose = "--quiet" not in sys.argv

    run_spot_check(target_path, verbose=verbose)
