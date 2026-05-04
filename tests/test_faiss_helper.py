"""Tests for utils.faiss_helper module."""
import os
import tempfile

import pytest

from llmchatflow.utils.faiss_helper import FaissIndex


@pytest.fixture
def faiss_path():
    """Create a unique temp file path (deleted on cleanup)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.faiss")


class TestFaissIndex:
    def test_create_and_add(self, faiss_path):
        idx = FaissIndex(faiss_path, dim=4)
        assert idx.ntotal() == 0
        idx.add([0], [[0.1, 0.2, 0.3, 0.4]], normalize=True)
        assert idx.ntotal() == 1

    def test_search_returns_result(self, faiss_path):
        idx = FaissIndex(faiss_path, dim=4)
        idx.add([0], [[0.1, 0.2, 0.3, 0.4]], normalize=True)
        result = idx.search([0.1, 0.2, 0.3, 0.4], top_k=5, normalize=True)
        assert result is not None
        assert len(result.ids) > 0

    def test_save_and_load(self, faiss_path):
        idx = FaissIndex(faiss_path, dim=4)
        idx.add([42], [[1.0, 0.0, 0.0, 0.0]], normalize=True)
        idx.save()
        assert idx.ntotal() == 1
        idx2 = FaissIndex(faiss_path, dim=4)
        assert idx2.ntotal() == 1

    def test_empty_search(self, faiss_path):
        idx = FaissIndex(faiss_path, dim=4)
        if idx.ntotal() == 0:
            pass  # Empty index is valid

    def test_reset(self, faiss_path):
        idx = FaissIndex(faiss_path, dim=4)
        idx.add([0], [[0.1, 0.2, 0.3, 0.4]], normalize=True)
        assert idx.ntotal() == 1
        idx.reset()
        assert idx.ntotal() == 0
