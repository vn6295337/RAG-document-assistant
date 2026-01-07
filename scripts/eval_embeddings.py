#!/usr/bin/env python3
"""
Embedding quality evaluation.

Usage:
    python scripts/eval_embeddings.py tests/eval_data/queries.json

Measures:
- Cosine similarity for similar text pairs (should be high)
- Cosine similarity for dissimilar text pairs (should be low)
"""

import sys
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class EmbeddingMetrics:
    """Metrics for embedding quality."""
    similar_pairs_avg: float
    similar_pairs_min: float
    dissimilar_pairs_avg: float
    dissimilar_pairs_max: float
    separation: float  # similar_avg - dissimilar_avg
    similar_results: List[Tuple[str, str, float]]
    dissimilar_results: List[Tuple[str, str, float]]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_embedding(text: str, model=None) -> List[float]:
    """Get embedding for text using sentence-transformers."""
    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')

    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def evaluate_embeddings(queries_file: str) -> EmbeddingMetrics:
    """Evaluate embedding quality using similarity pairs."""

    with open(queries_file, 'r') as f:
        data = json.load(f)

    similarity_pairs = data.get("similarity_pairs", {})
    similar = similarity_pairs.get("similar", [])
    dissimilar = similarity_pairs.get("dissimilar", [])

    if not similar and not dissimilar:
        print("No similarity pairs found in queries file")
        print("Expected format:")
        print('''  "similarity_pairs": {
    "similar": [["text1", "text2"], ...],
    "dissimilar": [["text1", "text2"], ...]
  }''')
        return None

    print("\n" + "=" * 60)
    print("  EMBEDDING QUALITY EVALUATION")
    print("=" * 60)

    # Load model once
    print("\nLoading embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print(f"Model: all-MiniLM-L6-v2 (384 dimensions)")

    # Evaluate similar pairs
    similar_scores = []
    similar_results = []

    print(f"\n📊 Similar Pairs ({len(similar)} pairs)")
    print("   Expected: cosine similarity > 0.6")
    print()

    for pair in similar:
        if len(pair) != 2:
            continue
        text1, text2 = pair
        emb1 = model.encode(text1, convert_to_numpy=True)
        emb2 = model.encode(text2, convert_to_numpy=True)
        score = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        similar_scores.append(score)
        similar_results.append((text1, text2, score))

        status = "✅" if score > 0.6 else "⚠️" if score > 0.4 else "❌"
        print(f"   {status} {score:.3f}: \"{text1[:30]}...\" vs \"{text2[:30]}...\"")

    # Evaluate dissimilar pairs
    dissimilar_scores = []
    dissimilar_results = []

    print(f"\n📊 Dissimilar Pairs ({len(dissimilar)} pairs)")
    print("   Expected: cosine similarity < 0.4")
    print()

    for pair in dissimilar:
        if len(pair) != 2:
            continue
        text1, text2 = pair
        emb1 = model.encode(text1, convert_to_numpy=True)
        emb2 = model.encode(text2, convert_to_numpy=True)
        score = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        dissimilar_scores.append(score)
        dissimilar_results.append((text1, text2, score))

        status = "✅" if score < 0.4 else "⚠️" if score < 0.6 else "❌"
        print(f"   {status} {score:.3f}: \"{text1[:30]}...\" vs \"{text2[:30]}...\"")

    # Calculate metrics
    metrics = EmbeddingMetrics(
        similar_pairs_avg=np.mean(similar_scores) if similar_scores else 0.0,
        similar_pairs_min=np.min(similar_scores) if similar_scores else 0.0,
        dissimilar_pairs_avg=np.mean(dissimilar_scores) if dissimilar_scores else 0.0,
        dissimilar_pairs_max=np.max(dissimilar_scores) if dissimilar_scores else 0.0,
        separation=(np.mean(similar_scores) - np.mean(dissimilar_scores)
                   if similar_scores and dissimilar_scores else 0.0),
        similar_results=similar_results,
        dissimilar_results=dissimilar_results
    )

    # Print summary
    print("\n" + "-" * 60)
    print("  SUMMARY")
    print("-" * 60)

    if similar_scores:
        print(f"  Similar pairs avg: {metrics.similar_pairs_avg:.3f}")
        print(f"  Similar pairs min: {metrics.similar_pairs_min:.3f}")

    if dissimilar_scores:
        print(f"  Dissimilar pairs avg: {metrics.dissimilar_pairs_avg:.3f}")
        print(f"  Dissimilar pairs max: {metrics.dissimilar_pairs_max:.3f}")

    print(f"  Separation (similar - dissimilar): {metrics.separation:.3f}")

    # Quality assessment
    print("\n📈 Quality Assessment")

    if metrics.similar_pairs_avg >= 0.6:
        print("  ✅ Similar pairs: GOOD (avg ≥ 0.6)")
    elif metrics.similar_pairs_avg >= 0.4:
        print("  ⚠️ Similar pairs: FAIR (avg 0.4-0.6)")
    else:
        print("  ❌ Similar pairs: POOR (avg < 0.4)")

    if metrics.dissimilar_pairs_avg <= 0.4:
        print("  ✅ Dissimilar pairs: GOOD (avg ≤ 0.4)")
    elif metrics.dissimilar_pairs_avg <= 0.6:
        print("  ⚠️ Dissimilar pairs: FAIR (avg 0.4-0.6)")
    else:
        print("  ❌ Dissimilar pairs: POOR (avg > 0.6)")

    if metrics.separation >= 0.3:
        print("  ✅ Separation: GOOD (≥ 0.3)")
    elif metrics.separation >= 0.15:
        print("  ⚠️ Separation: FAIR (0.15-0.3)")
    else:
        print("  ❌ Separation: POOR (< 0.15)")

    return metrics


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/eval_embeddings.py queries.json")
        print("\nExample:")
        print("  python scripts/eval_embeddings.py tests/eval_data/queries.json")
        sys.exit(1)

    queries_file = sys.argv[1]

    if not Path(queries_file).exists():
        print(f"Error: File not found: {queries_file}")
        sys.exit(1)

    metrics = evaluate_embeddings(queries_file)

    if metrics and metrics.separation < 0.15:
        sys.exit(1)
