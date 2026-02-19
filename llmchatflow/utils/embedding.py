import math
from typing import List
from sentence_transformers import SentenceTransformer


class SentenceEmbedding:
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", dim: int = 512):
        self.model_name = model_name
        # Load the model directly
        self.model = SentenceTransformer(model_name)

        # Update dim from model if possible
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            d = self.model.get_sentence_embedding_dimension()
            if d:
                self.dim = int(d)
        else:
            self.dim = dim

    def embed(self, text: str) -> List[float]:
        # Generate normalized embeddings
        embeddings = self.model.encode([text], normalize_embeddings=True)
        return embeddings[0].tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return s / (na * nb)
