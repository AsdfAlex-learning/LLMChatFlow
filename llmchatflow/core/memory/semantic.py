from typing import List, Dict
from ...utils.embedding import cosine_similarity


def semantic_scores(current_embedding: List[float], records: List[Dict]) -> List[float]:
    """Compute cosine similarity between a query embedding and stored memory embeddings.

    Used as a FAISS-free fallback when the vector index is unavailable.

    Args:
        current_embedding: The query vector.
        records: Memory records, each optionally containing an 'embedding' list.

    Returns:
        List of similarity scores (clamped to [0.0, 1.0]) aligned with records.
    """
    scores = []
    for r in records:
        emb = r.get("embedding") or []
        scores.append(max(0.0, cosine_similarity(current_embedding, emb)))
    return scores
