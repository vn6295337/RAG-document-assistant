#!/usr/bin/env python3
"""
Retrieval quality evaluation.

Usage:
    python scripts/eval_retrieval.py tests/eval_data/queries.json

Measures:
- Precision@k
- Recall@k
- Mean Reciprocal Rank (MRR)
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class RetrievalMetrics:
    """Metrics for a single query."""
    query_id: str
    query: str
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    retrieved_ids: List[str]
    relevant_found: List[str]
    relevant_missed: List[str]


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all queries."""
    total_queries: int
    mean_precision: float
    mean_recall: float
    mrr: float  # Mean Reciprocal Rank
    queries_with_hits: int


def evaluate_single_query(
    query_id: str,
    query: str,
    relevant_chunks: Set[str],
    retrieved_chunks: List[str],
    k: int = 5
) -> RetrievalMetrics:
    """Evaluate retrieval for a single query."""

    top_k = retrieved_chunks[:k]
    top_k_set = set(top_k)

    # Precision@k: relevant in top-k / k
    relevant_in_top_k = top_k_set & relevant_chunks
    precision = len(relevant_in_top_k) / k if k > 0 else 0.0

    # Recall@k: relevant in top-k / total relevant
    recall = len(relevant_in_top_k) / len(relevant_chunks) if relevant_chunks else 0.0

    # Reciprocal Rank: 1 / rank of first relevant
    reciprocal_rank = 0.0
    for i, chunk_id in enumerate(top_k):
        if chunk_id in relevant_chunks:
            reciprocal_rank = 1.0 / (i + 1)
            break

    return RetrievalMetrics(
        query_id=query_id,
        query=query,
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        retrieved_ids=top_k,
        relevant_found=list(relevant_in_top_k),
        relevant_missed=list(relevant_chunks - top_k_set)
    )


def run_retrieval_eval(
    queries_file: str,
    k: int = 5,
    use_mock: bool = False
) -> AggregateMetrics:
    """Run retrieval evaluation from queries file."""

    with open(queries_file, 'r') as f:
        data = json.load(f)

    queries = data.get("queries", [])

    if not queries:
        print("No queries found in file")
        return None

    # Import retrieval function
    if not use_mock:
        try:
            from src.retrieval.hybrid import hybrid_search
        except ImportError:
            print("Warning: Could not import hybrid_search, using mock")
            use_mock = True

    all_metrics = []

    print("\n" + "=" * 60)
    print("  RETRIEVAL QUALITY EVALUATION")
    print("=" * 60)

    for q in queries:
        query_id = q.get("id", "unknown")
        query_text = q.get("query", "")
        relevant = set(q.get("relevant_chunks", []))

        if not relevant:
            print(f"\n⚠️ Query {query_id}: No relevant chunks defined, skipping")
            continue

        print(f"\n📝 Query {query_id}: {query_text[:50]}...")

        # Get retrieval results
        if use_mock:
            # Mock results for testing without Pinecone
            retrieved = list(relevant)[:k] + ["mock::0", "mock::1"]
        else:
            try:
                results = hybrid_search(query_text, top_k=k)
                retrieved = [r.get("id", "") for r in results]
            except Exception as e:
                print(f"   Error: {e}")
                retrieved = []

        # Evaluate
        metrics = evaluate_single_query(
            query_id=query_id,
            query=query_text,
            relevant_chunks=relevant,
            retrieved_chunks=retrieved,
            k=k
        )
        all_metrics.append(metrics)

        # Print results
        print(f"   Precision@{k}: {metrics.precision_at_k:.2f}")
        print(f"   Recall@{k}: {metrics.recall_at_k:.2f}")
        print(f"   Reciprocal Rank: {metrics.reciprocal_rank:.2f}")
        if metrics.relevant_found:
            print(f"   ✅ Found: {metrics.relevant_found}")
        if metrics.relevant_missed:
            print(f"   ❌ Missed: {metrics.relevant_missed}")

    # Aggregate
    if not all_metrics:
        print("\nNo queries evaluated")
        return None

    aggregate = AggregateMetrics(
        total_queries=len(all_metrics),
        mean_precision=sum(m.precision_at_k for m in all_metrics) / len(all_metrics),
        mean_recall=sum(m.recall_at_k for m in all_metrics) / len(all_metrics),
        mrr=sum(m.reciprocal_rank for m in all_metrics) / len(all_metrics),
        queries_with_hits=sum(1 for m in all_metrics if m.reciprocal_rank > 0)
    )

    # Print summary
    print("\n" + "-" * 60)
    print("  SUMMARY")
    print("-" * 60)
    print(f"  Total queries: {aggregate.total_queries}")
    print(f"  Mean Precision@{k}: {aggregate.mean_precision:.2f}")
    print(f"  Mean Recall@{k}: {aggregate.mean_recall:.2f}")
    print(f"  MRR: {aggregate.mrr:.2f}")
    print(f"  Queries with hits: {aggregate.queries_with_hits}/{aggregate.total_queries}")

    # Quality assessment
    print("\n📊 Quality Assessment")
    if aggregate.mean_precision >= 0.6:
        print("  ✅ Precision: GOOD (≥60%)")
    elif aggregate.mean_precision >= 0.4:
        print("  ⚠️ Precision: FAIR (40-60%)")
    else:
        print("  ❌ Precision: POOR (<40%)")

    if aggregate.mrr >= 0.5:
        print("  ✅ MRR: GOOD (≥0.5)")
    elif aggregate.mrr >= 0.3:
        print("  ⚠️ MRR: FAIR (0.3-0.5)")
    else:
        print("  ❌ MRR: POOR (<0.3)")

    return aggregate


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/eval_retrieval.py queries.json [--mock]")
        print("\nExample:")
        print("  python scripts/eval_retrieval.py tests/eval_data/queries.json")
        print("  python scripts/eval_retrieval.py tests/eval_data/queries.json --mock")
        sys.exit(1)

    queries_file = sys.argv[1]
    use_mock = "--mock" in sys.argv
    k = 5

    # Parse k value if provided
    for arg in sys.argv:
        if arg.startswith("--k="):
            k = int(arg.split("=")[1])

    if not Path(queries_file).exists():
        print(f"Error: File not found: {queries_file}")
        sys.exit(1)

    metrics = run_retrieval_eval(queries_file, k=k, use_mock=use_mock)

    if metrics and metrics.mean_precision < 0.4:
        sys.exit(1)
