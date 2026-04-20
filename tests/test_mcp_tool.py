"""Unit tests for app/mcp_tool.py."""
from unittest.mock import patch

import pytest

import mcp_tool


SAMPLE_ASK_RESULT = {
    "answer": "You get 15 days of PTO per year.",
    "sources": [{"title": "PTO Policy", "url": "https://example.com", "doc_id": "hr-002"}],
    "no_results": False,
}


class TestGleanChat:
    def test_returns_ask_result(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            result = mcp_tool.glean_chat("What is PTO?")

        assert result == SAMPLE_ASK_RESULT
        mock_ask.assert_called_once_with(
            question="What is PTO?",
            top_k=5,
            include_citations=True,
        )

    def test_strips_whitespace_from_question(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            mcp_tool.glean_chat("  How much PTO?  ")

        mock_ask.assert_called_once_with(
            question="How much PTO?",
            top_k=5,
            include_citations=True,
        )

    def test_raises_on_empty_question(self):
        with pytest.raises(ValueError, match="required"):
            mcp_tool.glean_chat("")

    def test_raises_on_whitespace_only_question(self):
        with pytest.raises(ValueError, match="required"):
            mcp_tool.glean_chat("   ")

    def test_custom_top_k(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            mcp_tool.glean_chat("query", top_k=10)

        mock_ask.assert_called_once_with(question="query", top_k=10, include_citations=True)

    def test_none_top_k_defaults_to_5(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            mcp_tool.glean_chat("query", top_k=None)

        mock_ask.assert_called_once_with(question="query", top_k=5, include_citations=True)

    def test_none_include_citations_defaults_to_true(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            mcp_tool.glean_chat("query", include_citations=None)

        mock_ask.assert_called_once_with(question="query", top_k=5, include_citations=True)

    def test_include_citations_false(self):
        with patch("mcp_tool.ask", return_value=SAMPLE_ASK_RESULT) as mock_ask:
            mcp_tool.glean_chat("query", include_citations=False)

        mock_ask.assert_called_once_with(question="query", top_k=5, include_citations=False)
