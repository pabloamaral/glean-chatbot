"""Unit tests for app/chatbot.py."""
from unittest.mock import patch

import pytest

import chatbot


SAMPLE_RESULTS = [
    {"title": "PTO Policy", "url": "https://example.com/pto", "doc_id": "hr-002", "snippet": "15 days."},
]


class TestAsk:
    def test_returns_answer_and_sources(self):
        with patch("chatbot.search", return_value=SAMPLE_RESULTS), \
             patch("chatbot.chat", return_value="You get 15 days."):
            result = chatbot.ask("What is PTO?")

        assert result["answer"] == "You get 15 days."
        assert result["no_results"] is False
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "PTO Policy"
        assert result["sources"][0]["doc_id"] == "hr-002"

    def test_no_results_sets_flag(self):
        with patch("chatbot.search", return_value=[]), \
             patch("chatbot.chat", return_value="No info found."):
            result = chatbot.ask("Unknown topic")

        assert result["no_results"] is True
        assert result["sources"] == []

    def test_include_citations_false_omits_sources(self):
        with patch("chatbot.search", return_value=SAMPLE_RESULTS), \
             patch("chatbot.chat", return_value="Answer."):
            result = chatbot.ask("What is PTO?", include_citations=False)

        assert result["sources"] == []

    def test_passes_top_k_to_search(self):
        with patch("chatbot.search", return_value=[]) as mock_search, \
             patch("chatbot.chat", return_value="Answer."):
            chatbot.ask("query", top_k=3)

        mock_search.assert_called_once_with("query", top_k=3)

    def test_passes_search_results_to_chat(self):
        with patch("chatbot.search", return_value=SAMPLE_RESULTS), \
             patch("chatbot.chat", return_value="Answer.") as mock_chat:
            chatbot.ask("What is PTO?")

        mock_chat.assert_called_once_with("What is PTO?", SAMPLE_RESULTS)


class TestPrintResponse:
    def test_prints_answer(self, capsys):
        chatbot._print_response({"answer": "Test answer.", "sources": [], "no_results": False})
        captured = capsys.readouterr()
        assert "Test answer." in captured.out

    def test_prints_sources(self, capsys):
        response = {
            "answer": "Answer here.",
            "sources": [{"title": "Doc A", "doc_id": "hr-001", "url": "https://example.com"}],
            "no_results": False,
        }
        chatbot._print_response(response)
        captured = capsys.readouterr()
        assert "Doc A" in captured.out
        assert "hr-001" in captured.out

    def test_prints_no_results_note(self, capsys):
        chatbot._print_response({"answer": "N/A", "sources": [], "no_results": True})
        captured = capsys.readouterr()
        assert "No matching documents" in captured.out
