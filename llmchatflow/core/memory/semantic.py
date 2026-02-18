from typing import List, Dict
from ...utils.embedding import cosine_similarity


def semantic_scores(current_embedding: List[float], records: List[Dict]) -> List[float]:
    scores = []
    for r in records:
        emb = r.get("embedding") or []
        scores.append(max(0.0, cosine_similarity(current_embedding, emb)))
    return scores
