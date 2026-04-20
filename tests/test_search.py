"""Unit tests for app/search.py."""
from unittest.mock import MagicMock, patch

import pytest

import search as search_module


def _mock_response(status_code: int, json_body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = str(json_body)
    return resp


SAMPLE_RESULT = {
    "document": {
        "title": "PTO Policy",
        "url": "https://internal.banksandbanjo.com/hr/banks-banjo-hr-002",
        "id": "banks-banjo-hr-002",
    },
    "snippets": [
        {"text": "Employees accrue 15 days per year."},
        {"text": "Unused PTO rolls over up to 5 days."},
    ],
}


class TestSearch:
    def test_returns_parsed_results(self):
        payload = {"results": [SAMPLE_RESULT]}
        with patch("search.requests.post", return_value=_mock_response(200, payload)):
            results = search_module.search("What is the PTO policy?")

        assert len(results) == 1
        r = results[0]
        assert r["title"] == "PTO Policy"
        assert r["doc_id"] == "banks-banjo-hr-002"
        assert r["url"] == "https://internal.banksandbanjo.com/hr/banks-banjo-hr-002"
        assert "Employees accrue 15 days per year." in r["snippet"]
        assert "Unused PTO rolls over up to 5 days." in r["snippet"]

    def test_returns_empty_list_when_no_results(self):
        payload = {"results": []}
        with patch("search.requests.post", return_value=_mock_response(200, payload)):
            results = search_module.search("unknown query")
        assert results == []

    def test_returns_empty_list_when_results_key_missing(self):
        payload = {}
        with patch("search.requests.post", return_value=_mock_response(200, payload)):
            results = search_module.search("unknown query")
        assert results == []

    def test_raises_on_non_200(self):
        with patch("search.requests.post", return_value=_mock_response(401, {})):
            with pytest.raises(RuntimeError, match="Search API error 401"):
                search_module.search("What is the PTO policy?")

    def test_snippet_strips_whitespace(self):
        result_with_spaces = {
            "document": {"title": "Test", "url": "", "id": "test-id"},
            "snippets": [{"text": "  leading and trailing  "}, {"text": "  "}],
        }
        payload = {"results": [result_with_spaces]}
        with patch("search.requests.post", return_value=_mock_response(200, payload)):
            results = search_module.search("query")

        assert results[0]["snippet"] == "leading and trailing"

    def test_missing_snippet_text_is_skipped(self):
        result_no_text = {
            "document": {"title": "Test", "url": "", "id": "test-id"},
            "snippets": [{"other_key": "value"}],
        }
        payload = {"results": [result_no_text]}
        with patch("search.requests.post", return_value=_mock_response(200, payload)):
            results = search_module.search("query")

        assert results[0]["snippet"] == ""

    def test_passes_top_k_as_page_size(self):
        payload = {"results": []}
        with patch("search.requests.post", return_value=_mock_response(200, payload)) as mock_post:
            search_module.search("query", top_k=3)

        sent_payload = mock_post.call_args.kwargs["json"]
        assert sent_payload["pageSize"] == 3
