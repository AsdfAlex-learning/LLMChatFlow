import math
import hashlib
from typing import List
import tiktoken


class SimpleEmbedding:
    def __init__(self, model_name: str = "bge-small-zh-v1.5", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        try:
            self.enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.enc = None

    def _hash_token(self, token: int) -> int:
        h = hashlib.sha256(str(token).encode()).hexdigest()
        return int(h[:8], 16)

    def embed(self, text: str) -> List[float]:
        if not self.enc:
            v = [0.0] * self.dim
            return v
        tokens = self.enc.encode(text)
        v = [0.0] * self.dim
        for tk in tokens:
            idx = self._hash_token(tk) % self.dim
            v[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return s / (na * nb)
