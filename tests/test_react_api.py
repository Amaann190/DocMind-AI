"""HTTP regressions for the separate React backend; no live model is required."""
import importlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM
from utils.session_workspace import clear_session_workspace

api = importlib.import_module("backend.app")
HEADERS = {"X-DocMind-Client": "react"}


class ReactApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app, headers=HEADERS)
        self.client.post("/api/session").raise_for_status()
        self.state = api.sessions[self.client.cookies[api.COOKIE]]
        self.clients = [self.client]

    def tearDown(self):
        for client in self.clients:
            state = api.sessions.pop(client.cookies.get(api.COOKIE), None)
            if state:
                clear_session_workspace(state)
            client.close()

    def embedding(self, *args):
        model = MockEmbedding(embed_dim=8)
        api.indexer.st.session_state["embedding_model"] = model
        api.indexer.st.session_state["embedding_config"] = {"model": "mock", "chunk_size": 256, "chunk_overlap": 32}
        return model

    def ingest_sample(self):
        with patch.object(api.indexer, "setup_embedding_model", side_effect=self.embedding), \
                patch.object(api.ollama, "create_llm", return_value=MockLLM()):
            response = self.client.post("/api/import", json={"kind": "sample"})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_read_upload_chat_source_preview_clear_and_reupload(self):
        result = self.ingest_sample()
        self.assertTrue(result["has_index"])
        self.assertIn("November 12", result["sources"][0]["preview"])
        llm = Mock()
        llm.stream_chat.return_value = iter([SimpleNamespace(delta="The launch is November 12, 2026 [1].")])
        with patch.object(api.ollama, "create_llm", return_value=llm):
            response = self.client.post("/api/chat", json={"text": "When does Aurora launch?"})
        events = [json.loads(line) for line in response.text.splitlines()]
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(events[-1]["message"]["sources"])
        export = self.client.get("/api/export")
        self.assertEqual(export.content[:2], b"PK")
        cleared = self.client.delete("/api/sources").json()
        self.assertFalse(cleared["has_index"])
        self.assertEqual(cleared["sources"], [])
        llm.stream_chat.return_value = iter([SimpleNamespace(delta="No documents loaded.")])
        with patch.object(api.ollama, "create_llm", return_value=llm):
            self.client.post("/api/chat", json={"text": "What was the launch date?"})
        sent = " ".join(m.content for m in llm.stream_chat.call_args.args[0])
        self.assertNotIn("November 12", sent)
        self.assertTrue(self.ingest_sample()["has_index"])

    def test_partial_upload_reports_empty_file_and_retains_good_file(self):
        with patch.object(api.indexer, "setup_embedding_model", side_effect=self.embedding), \
                patch.object(api.ollama, "create_llm", return_value=MockLLM()):
            response = self.client.post("/api/upload", files=[
                ("files", ("fact.txt", b"Approval code ORBIT-7429", "text/plain")),
                ("files", ("empty.txt", b"", "text/plain"))])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["warnings"]), 1)
        self.assertEqual(response.json()["sources"][0]["name"], "fact.txt")

    def test_sessions_and_credentials_are_isolated(self):
        self.ingest_sample()
        second = TestClient(api.app, headers=HEADERS)
        self.clients.append(second)
        self.assertEqual(second.post("/api/session").json()["sources"], [])
        config = self.client.get("/api/state").json()["settings"]
        config["api_key"] = "private-test-key"
        response = self.client.put("/api/settings", json=config)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("private-test-key", response.text)
        self.assertNotIn("api_key", response.json()["settings"])
        self.assertFalse(response.json()["has_index"])
        self.assertEqual(second.get("/api/state").json()["messages"], [])

    def test_cross_origin_missing_header_and_path_traversal_are_rejected(self):
        self.assertEqual(self.client.post("/api/session", headers={"Origin": "https://untrusted.example"}).status_code, 403)
        with TestClient(api.app) as anonymous:
            self.assertEqual(anonymous.post("/api/session").status_code, 403)
            self.assertEqual(anonymous.get("/api/state").status_code, 401)
        response = self.client.post("/api/upload", files=[("files", ("../secret.txt", b"test", "text/plain"))])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/import", json={"kind": "website", "value": "http://localhost/secret"}).status_code, 400)

    def test_settings_validation_and_busy_conflicts(self):
        config = self.client.get("/api/state").json()["settings"]
        config.update(chunk_size=64, overlap=64)
        self.assertEqual(self.client.put("/api/settings", json=config).status_code, 422)
        self.state["lock"].acquire()
        try:
            self.assertEqual(self.client.post("/api/chat", json={"text": "Hello"}).status_code, 409)
            self.assertEqual(self.client.delete("/api/sources").status_code, 409)
        finally:
            self.state["lock"].release()

    def test_remote_cleanup_failure_preserves_owned_ids_and_blocks_reset(self):
        self.state.update(r2r_document_ids=["owned"], r2r_document_origin={"base_url": "http://localhost:7272", "api_key": ""})
        with patch("utils.r2r.R2RClient.delete_documents", return_value=["owned"]):
            self.assertEqual(self.client.delete("/api/session").status_code, 502)
        self.assertEqual(self.state["r2r_document_ids"], ["owned"])
        self.assertTrue(self.state["r2r_ingestion_failed"])


if __name__ == "__main__":
    unittest.main()
