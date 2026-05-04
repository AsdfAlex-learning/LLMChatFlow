"""Test fixtures and configuration for LLMChatFlow tests."""
import os
import tempfile
from typing import Any, Dict, Generator

import pytest


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database path for SQLite + FAISS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_memory.db")
        yield path


@pytest.fixture
def sample_memory_record() -> Dict[str, Any]:
    """A sample memory record for testing."""
    return {
        "id": "test-uuid-001",
        "uuid": "test-uuid-001",
        "turn_id": "turn-001",
        "user_id": "user1",
        "session_id": "session1",
        "role": "user",
        "text": "Hello, this is a test message.",
        "memory_type": "episodic",
        "memory_scope": "session",
        "importance": 0.8,
        "decay_rate": 0.1,
        "timestamp": 1000000,
        "similarity": 0.75,
        "metadata": {},
    }
