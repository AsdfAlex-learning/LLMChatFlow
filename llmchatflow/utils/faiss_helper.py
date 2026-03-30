from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple, Optional
import os

import numpy as np


def _require_faiss():
    try:
        import faiss  # type: ignore

        return faiss
    except Exception as e:
        raise ImportError("faiss is required for FAISS index operations") from e


def _as_float32_matrix(vectors: Iterable[Iterable[float]], dim: int) -> np.ndarray:
    arr = np.asarray(list(vectors), dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != dim:
        raise ValueError(f"vectors must be shape (n, {dim})")
    return arr


def _l2_normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


@dataclass
class FaissSearchResult:
    ids: np.ndarray
    scores: np.ndarray


class FaissIndex:
    def __init__(self, index_path: str, dim: int):
        self.index_path = str(index_path)
        self.dim = int(dim)
        self._faiss = _require_faiss()
        self._index = self._load_or_create()

    def _load_or_create(self):
        path = Path(self.index_path)
        if path.exists():
            idx = self._faiss.read_index(str(path))
            return idx
        base = self._faiss.IndexFlatIP(self.dim)
        idx = self._faiss.IndexIDMap2(base)
        return idx

    def save(self) -> None:
        path = Path(self.index_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        self._faiss.write_index(self._index, str(tmp))
        os.replace(str(tmp), str(path))

    def add(self, ids: Iterable[int], vectors: Iterable[Iterable[float]], normalize: bool = True) -> None:
        id_arr = np.asarray(list(ids), dtype=np.int64)
        if id_arr.ndim != 1:
            raise ValueError("ids must be a 1D array-like")
        vec = _as_float32_matrix(vectors, self.dim)
        if normalize:
            vec = _l2_normalize(vec)
        self._index.add_with_ids(vec, id_arr)
        self.save()

    def search(self, vector: Iterable[float], top_k: int, normalize: bool = True) -> FaissSearchResult:
        q = np.asarray([list(vector)], dtype=np.float32)
        if q.shape[1] != self.dim:
            raise ValueError(f"query vector must have dim {self.dim}")
        if normalize:
            q = _l2_normalize(q)
        scores, ids = self._index.search(q, int(top_k))
        return FaissSearchResult(ids=ids[0], scores=scores[0])

    def reset(self) -> None:
        base = self._faiss.IndexFlatIP(self.dim)
        self._index = self._faiss.IndexIDMap2(base)
        self.save()

    def ntotal(self) -> int:
        return int(self._index.ntotal)
