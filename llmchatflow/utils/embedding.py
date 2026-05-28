import math
import re
import unicodedata
import logging
import threading
from typing import List, Optional
from llmchatflow.config import load_config


class SentenceEmbedding:
    """Thread-safe sentence embedding wrapper using SentenceTransformers.

    Handles model loading, text normalization, embedding generation,
    and graceful fallback to zero vectors on failure.
    """

    def __init__(self, model_name: Optional[str] = None, dim: int = 512, device: Optional[str] = None):
        from sentence_transformers import SentenceTransformer

        cfg = load_config()
        chosen_model = model_name or getattr(cfg, "embedding_model", "BAAI/bge-small-zh-v1.5")
        chosen_device = device if device is not None else (getattr(cfg, "embedding_device", "") or None)
        self.model_name = chosen_model
        self.model = SentenceTransformer(chosen_model, device=chosen_device)

        # Update dim from model if possible
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            d = self.model.get_sentence_embedding_dimension()
            if d:
                self.dim = int(d)
        else:
            self.dim = dim

        self._logger = logging.getLogger(__name__)
        self._lock = threading.Lock()

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", text)
        t = t.replace("\r\n", "\n").replace("\r", "\n")
        t = re.sub(r"\s+", " ", t)
        t = t.strip()
        return t

    def embed(self, text: str) -> List[float]:
        """Encode text into a normalized embedding vector.

        Returns a zero vector on empty input or encoding failure.
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            return [0.0] * int(getattr(self, "dim", 0) or 0)
        with self._lock:
            try:
                embeddings = self.model.encode([cleaned], normalize_embeddings=True)
                return embeddings[0].tolist()
            except Exception as e:
                self._logger.warning("Failed to generate embedding (%s)", str(e))
                return [0.0] * int(getattr(self, "dim", 0) or 0)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Returns 0.0 if either vector is empty or dimensions mismatch.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return s / (na * nb)
