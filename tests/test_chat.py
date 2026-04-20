"""Unit tests for app/chat.py."""
from unittest.mock import MagicMock, patch

import pytest

import chat as chat_module


def _mock_response(status_code: int, json_body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


SAMPLE_SOURCES = [
    {"title": "PTO Policy", "snippet": "15 days per year.", "url": "https://example.com/pto", "doc_id": "hr-002"},
]


class TestBuildMessage:
    def test_with_results_includes_context(self):
        msg = chat_module._build_message("What is PTO?", SAMPLE_SOURCES)
        assert "What is PTO?" in msg
        assert "PTO Policy" in msg
        assert "15 days per year." in msg
        assert "Context from internal documents" in msg

    def test_without_results_suggests_contact(self):
        msg = chat_module._build_message("What is PTO?", [])
        assert "people@banksandbanjo.com" in msg
        assert "No relevant internal" in msg

    def test_multiple_sources_are_numbered(self):
        sources = [
            {"title": "Doc A", "snippet": "Content A"},
            {"title": "Doc B", "snippet": "Content B"},
        ]
        msg = chat_module._build_message("question", sources)
        assert "[Source 1: Doc A]" in msg
        assert "[Source 2: Doc B]" in msg


class TestExtractAnswer:
    def test_extracts_from_glean_ai_author(self):
        response_json = {
            "messages": [
                {
                    "author": "USER",
                    "fragments": [{"text": "What is PTO?"}],
                },
                {
                    "author": "GLEAN_AI",
                    "fragments": [{"text": "You get 15 days."}, {"text": "It rolls over."}],
                },
            ]
        }
        answer = chat_module._extract_answer(response_json)
        assert "You get 15 days." in answer
        assert "It rolls over." in answer

    def test_extracts_from_assistant_author(self):
        response_json = {
            "messages": [
                {"author": "ASSISTANT", "fragments": [{"text": "The answer is 42."}]}
            ]
        }
        answer = chat_module._extract_answer(response_json)
        assert answer == "The answer is 42."

    def test_extracts_from_bot_author(self):
        response_json = {
            "messages": [
                {"author": "BOT", "fragments": [{"text": "Bot response here."}]}
            ]
        }
        answer = chat_module._extract_answer(response_json)
        assert answer == "Bot response here."

    def test_skips_empty_fragments(self):
        response_json = {
            "messages": [
                {
                    "author": "GLEAN_AI",
                    "fragments": [{"text": ""}, {"text": "   "}, {"text": "Real answer."}],
                }
            ]
        }
        answer = chat_module._extract_answer(response_json)
        assert answer == "Real answer."

    def test_prefers_last_ai_message(self):
        response_json = {
            "messages": [
                {"author": "GLEAN_AI", "fragments": [{"text": "First response."}]},
                {"author": "USER", "fragments": [{"text": "Follow-up."}]},
                {"author": "GLEAN_AI", "fragments": [{"text": "Second response."}]},
            ]
        }
        answer = chat_module._extract_answer(response_json)
        assert answer == "Second response."

    def test_falls_back_to_answer_key(self):
        response_json = {
            "messages": [{"author": "USER", "fragments": [{"text": "Hello"}]}],
            "answer": {"text": "Fallback answer."},
        }
        answer = chat_module._extract_answer(response_json)
        assert answer == "Fallback answer."

    def test_returns_default_when_no_answer(self):
        answer = chat_module._extract_answer({"messages": []})
        assert answer == "No answer returned from Chat API."


class TestChat:
    def test_returns_extracted_answer(self):
        response_body = {
            "messages": [
                {"author": "GLEAN_AI", "fragments": [{"text": "Here is your answer."}]}
            ]
        }
        with patch("chat.requests.post", return_value=_mock_response(200, response_body)):
            result = chat_module.chat("What is PTO?", SAMPLE_SOURCES)
        assert result == "Here is your answer."

    def test_raises_on_non_200(self):
        with patch("chat.requests.post", return_value=_mock_response(500, {})):
            with pytest.raises(RuntimeError, match="Chat API error 500"):
                chat_module.chat("What is PTO?", [])

    def test_sends_user_message_fragment(self):
        response_body = {"messages": [], "answer": {"text": "ok"}}
        with patch("chat.requests.post", return_value=_mock_response(200, response_body)) as mock_post:
            chat_module.chat("My question", [])

        payload = mock_post.call_args.kwargs["json"]
        assert payload["messages"][0]["author"] == "USER"
        assert payload["saveChat"] is False
        assert payload["stream"] is False
