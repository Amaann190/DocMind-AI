import os
import tempfile
import unittest
from unittest.mock import patch

import httpx

from utils.r2r import (
    R2RClient,
    R2RConnectionError,
    _extract_answer,
    _extract_document_id,
    r2r_is_ready,
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "text"

    def json(self):
        return self._payload


class R2RClientTests(unittest.TestCase):
    def test_health_true_when_server_responds(self):
        client = R2RClient(base_url="http://localhost:7272")
        with patch(
            "utils.r2r.httpx.request", return_value=_FakeResponse({}, 200)
        ) as request:
            self.assertTrue(client.health())
        request.assert_called_once()
        self.assertEqual(request.call_args.args[0], "GET")
        self.assertEqual(request.call_args.args[1], "http://localhost:7272/v3/health")

    def test_health_false_when_server_unreachable(self):
        client = R2RClient(base_url="http://localhost:7272")
        with patch(
            "utils.r2r.httpx.request",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            self.assertFalse(client.health())

    def test_upload_documents_returns_ids(self):
        client = R2RClient(base_url="http://localhost:7272")
        responses = [
            _FakeResponse({"results": {"document_id": "doc-1"}}),
            _FakeResponse({"results": [{"document_id": "doc-2"}]}),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            first = os.path.join(temp_dir, "a.txt")
            second = os.path.join(temp_dir, "b.txt")
            for path in (first, second):
                with open(path, "w") as handle:
                    handle.write("content")
            with patch("utils.r2r.httpx.request", side_effect=responses), patch("utils.r2r.uuid4", side_effect=["doc-1", "doc-2"]):
                document_ids = client.upload_documents([first, second])
        self.assertEqual(document_ids, ["doc-1", "doc-2"])

    def test_upload_documents_raises_on_bad_response(self):
        client = R2RClient(base_url="http://localhost:7272")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "a.txt")
            with open(path, "w") as handle:
                handle.write("content")
            with patch(
                "utils.r2r.httpx.request",
                return_value=_FakeResponse({"results": []}),
            ):
                with self.assertRaises(R2RConnectionError):
                    client.upload_documents([path])

    def test_rag_returns_answer(self):
        client = R2RClient(base_url="http://localhost:7272")
        with patch(
            "utils.r2r.httpx.request",
            return_value=_FakeResponse(
                {"results": {"rag_response": "The answer is 42."}}
            ),
        ) as request:
            answer = client.rag("What is the answer?", document_ids=["doc-1"])
        self.assertEqual(answer, "The answer is 42.")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["query"], "What is the answer?")
        self.assertEqual(payload["search_settings"]["filters"], {"document_id": {"$in": ["doc-1"]}})

    def test_rag_raises_when_answer_missing(self):
        client = R2RClient(base_url="http://localhost:7272")
        with patch(
            "utils.r2r.httpx.request",
            return_value=_FakeResponse({"results": {}}),
        ):
            with self.assertRaises(R2RConnectionError):
                client.rag("What is the answer?")

    def test_http_error_status_reports_unreachable(self):
        client = R2RClient(base_url="http://localhost:7272")
        with patch(
            "utils.r2r.httpx.request",
            return_value=_FakeResponse({"error": "bad"}, status_code=500),
        ):
            self.assertFalse(client.health())
            with self.assertRaises(R2RConnectionError):
                client.rag("question")

    def test_api_key_sent_as_bearer_token(self):
        client = R2RClient(base_url="http://localhost:7272", api_key="secret")
        with patch(
            "utils.r2r.httpx.request", return_value=_FakeResponse({}, 200)
        ) as request:
            client.health()
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer secret",
        )


class R2RHelpersTests(unittest.TestCase):
    def test_extract_document_id_single_shape(self):
        self.assertEqual(
            _extract_document_id({"results": {"document_id": "abc"}}),
            "abc",
        )

    def test_extract_document_id_bulk_shape(self):
        self.assertEqual(
            _extract_document_id(
                {"results": [{"document_id": "abc"}, {"document_id": "def"}]}
            ),
            "abc",
        )

    def test_extract_answer_prefers_rag_response(self):
        payload = {"results": {"rag_response": "A", "generated_answer": "B"}}
        self.assertEqual(_extract_answer(payload), "A")

    def test_extract_answer_falls_back_to_generated_answer(self):
        payload = {"results": {"generated_answer": "B"}}
        self.assertEqual(_extract_answer(payload), "B")

    def test_r2r_is_ready_requires_enabled_and_documents(self):
        self.assertFalse(r2r_is_ready({"r2r_enabled": True}))
        self.assertFalse(
            r2r_is_ready({"r2r_enabled": True, "r2r_document_ids": []})
        )
        self.assertFalse(
            r2r_is_ready({"r2r_document_ids": ["doc-1"]})
        )
        self.assertTrue(
            r2r_is_ready({"r2r_enabled": True, "r2r_document_ids": ["doc-1"]})
        )


if __name__ == "__main__":
    unittest.main()
