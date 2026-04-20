"""Unit tests for app/indexer.py."""
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

import indexer


class TestBuildDocument:
    def test_returns_expected_shape(self):
        doc = indexer.build_document("01_welcome_and_onboarding.txt", "Hello world")
        assert doc["datasource"] == indexer.DATASOURCE
        assert doc["objectType"] == "HRDocument"
        assert doc["id"] == "banks-banjo-hr-001"
        assert doc["title"] == "Welcome to Banks & Banjo LLC — New Employee Onboarding Guide"
        assert doc["body"]["mimeType"] == "text/plain"
        assert doc["body"]["textContent"] == "Hello world"
        assert doc["viewURL"] == "https://internal.banksandbanjo.com/hr/banks-banjo-hr-001"
        assert doc["permissions"]["allowAllDatasourceUsersAccess"] is True

    def test_all_known_filenames_are_valid(self):
        for filename, meta in indexer.DOC_METADATA.items():
            doc = indexer.build_document(filename, "content")
            assert doc["id"] == meta["id"]
            assert doc["title"] == meta["title"]

    def test_unknown_filename_raises_key_error(self):
        with pytest.raises(KeyError):
            indexer.build_document("unknown_file.txt", "content")


class TestLoadDocuments:
    def test_loads_existing_files(self, tmp_path):
        """All five known files present — should return five documents."""
        for filename in indexer.DOC_METADATA:
            (tmp_path / filename).write_text("sample content", encoding="utf-8")

        with patch.object(indexer, "DOCUMENTS_DIR", tmp_path):
            docs = indexer.load_documents()

        assert len(docs) == 5
        ids = {d["id"] for d in docs}
        assert ids == {meta["id"] for meta in indexer.DOC_METADATA.values()}

    def test_skips_missing_files(self, tmp_path):
        """Only one file present — the rest are skipped."""
        first_filename = next(iter(indexer.DOC_METADATA))
        (tmp_path / first_filename).write_text("content", encoding="utf-8")

        with patch.object(indexer, "DOCUMENTS_DIR", tmp_path):
            docs = indexer.load_documents()

        assert len(docs) == 1
        assert docs[0]["id"] == indexer.DOC_METADATA[first_filename]["id"]

    def test_returns_empty_when_no_files(self, tmp_path):
        with patch.object(indexer, "DOCUMENTS_DIR", tmp_path):
            docs = indexer.load_documents()
        assert docs == []


class TestBulkIndex:
    def _make_mock_response(self, status_code: int, json_body=None, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        if json_body is not None:
            response.json.return_value = json_body
        else:
            response.json.side_effect = ValueError("no json")
        return response

    def test_success(self):
        docs = [{"id": "doc-1"}]
        mock_resp = self._make_mock_response(200)

        with patch("indexer.requests.post", return_value=mock_resp) as mock_post:
            indexer.bulk_index(docs)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["json"]
        assert payload["documents"] == docs
        assert payload["datasource"] == indexer.DATASOURCE
        assert payload["isFirstPage"] is True
        assert payload["isLastPage"] is True

    def test_failure_raises_system_exit(self):
        docs = [{"id": "doc-1"}]
        mock_resp = self._make_mock_response(400, json_body={"error": "bad request"})

        with patch("indexer.requests.post", return_value=mock_resp):
            with pytest.raises(SystemExit):
                indexer.bulk_index(docs)

    def test_upload_id_is_valid_uuid(self):
        docs = [{"id": "doc-1"}]
        mock_resp = self._make_mock_response(200)

        with patch("indexer.requests.post", return_value=mock_resp) as mock_post:
            indexer.bulk_index(docs)

        payload = mock_post.call_args.kwargs["json"]
        # Should not raise if it's a valid UUID
        parsed = uuid.UUID(payload["uploadId"])
        assert str(parsed) == payload["uploadId"]
