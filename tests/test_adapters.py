"""Tests for APIAdapter and CLIAdapter."""
import sys
from io import StringIO
from unittest.mock import patch

from llmchatflow.adapters.api.adapter import APIAdapter
from llmchatflow.adapters.cli.adapter import CLIAdapter


class TestAPIAdapter:
    def test_parse_request(self):
        a = APIAdapter()
        result = a.parse_request({"session_id": "s1", "user_input": "hello"})
        assert result["session_id"] == "s1"
        assert result["user_input"] == "hello"

    def test_parse_request_defaults(self):
        a = APIAdapter()
        result = a.parse_request({})
        assert result["session_id"] == "default_session"
        assert result["user_input"] == ""

    def test_format_response(self):
        a = APIAdapter()
        result = a.format_response("hi there")
        assert result == {"response": "hi there"}


class TestCLIAdapter:
    def test_get_input(self):
        a = CLIAdapter()
        with patch("builtins.input", return_value="hello"):
            result = a.get_input()
            assert result == "hello"

    def test_get_input_eof(self):
        a = CLIAdapter()
        with patch("builtins.input", side_effect=EOFError):
            result = a.get_input()
            assert result == ""

    def test_show_output(self, capsys):
        a = CLIAdapter()
        a.show_output("test output")
        captured = capsys.readouterr()
        assert "test output" in captured.out

    def test_show_error(self, capsys):
        a = CLIAdapter()
        a.show_error("test error")
        captured = capsys.readouterr()
        assert "test error" in captured.err
