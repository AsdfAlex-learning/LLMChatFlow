"""Tests for core.prompt.assembler module."""
from llmchatflow.core.prompt.assembler import StructuredPromptAssembler


class TestStructuredPromptAssembler:
    def test_basic_assemble(self):
        assembler = StructuredPromptAssembler("test system prompt")
        result = assembler.assemble(
            {"system_prompt": "custom", "history_summary": "", "retrieved_memories": "some memory"},
            "user query",
        )
        assert len(result) == 3  # system + retrieved_memories + user
        assert result[0]["role"] == "system"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "user query"

    def test_no_memories(self):
        assembler = StructuredPromptAssembler()
        result = assembler.assemble(
            {"system_prompt": "", "history_summary": "", "retrieved_memories": ""},
            "hello",
        )
        assert len(result) == 2  # system (default) + user

    def test_multiple_blocks(self):
        assembler = StructuredPromptAssembler("sys")
        result = assembler.assemble(
            {"system_prompt": "s", "history_summary": "h", "retrieved_memories": "m"},
            "u",
        )
        assert len(result) == 4  # system + history + memory + user
