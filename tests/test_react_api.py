"""HTTP regressions for the separate React backend; no live model is required."""
import importlib
import json
import unittest
import tempfile
import threading
from pathlib import Path
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
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.history_path = patch.object(api.history, "DB_PATH", Path(self.storage.name) / "history.sqlite3")
        self.history_path.start()
        self.addCleanup(self.history_path.stop)
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

    def test_saved_conversations_rename_search_reopen_restart_and_owner_isolation(self):
        initial_id = self.state["conversation_id"]
        for _ in range(2):
            draft = self.client.post("/api/conversations").json()
            self.assertEqual(draft["conversation_id"], initial_id)
            self.assertFalse(draft["conversations"][0]["started"])
        with patch.object(api.ollama, "chat", return_value=iter(["Unique answer CEDAR-83"])):
            self.client.post("/api/chat", json={"text": "Remember this"}).raise_for_status()
        first = self.client.get("/api/state").json()["conversation_id"]
        self.assertEqual(self.state["title"], "Remember this")
        self.assertTrue(self.client.get("/api/state").json()["conversations"][0]["started"])
        self.client.put(f"/api/conversations/{first}", json={"title": "Research notes"}).raise_for_status()
        fresh = self.client.post("/api/conversations").json()
        self.assertEqual(fresh["messages"], [])
        self.assertEqual(len(fresh["conversations"]), 2)
        self.assertEqual(self.client.get("/api/conversations", params={"q": "CEDAR-83"}).json()[0]["id"], first)
        restored = self.client.post(f"/api/conversations/{first}/open").json()
        self.assertEqual(restored["messages"][-1]["content"], "Unique answer CEDAR-83")
        reused = self.client.post("/api/conversations").json()
        self.assertEqual(reused["conversation_id"], fresh["conversation_id"])
        self.assertEqual(len(reused["conversations"]), 2)
        self.client.post(f"/api/conversations/{first}/open").raise_for_status()
        token = self.client.cookies[api.COOKIE]
        api.sessions.pop(token)
        restarted = self.client.post("/api/session").json()
        self.state = api.sessions[token]
        self.assertEqual(restarted["title"], "Research notes")
        self.assertEqual(restarted["messages"], restored["messages"])
        self.assertEqual(self.state["chat_history_start"], 0)
        second = TestClient(api.app, headers=HEADERS)
        self.clients.append(second)
        second.post("/api/session")
        self.assertEqual(second.post(f"/api/conversations/{first}/open").status_code, 404)
        self.assertEqual(second.delete(f"/api/conversations/{first}").status_code, 404)
        self.assertEqual(second.get("/api/conversations", params={"q": "CEDAR"}).json(), [])
        self.client.delete(f"/api/conversations/{first}").raise_for_status()
        self.assertEqual(self.client.get("/api/conversations", params={"q": "CEDAR"}).json(), [])
        self.client.delete("/api/session").raise_for_status()
        self.assertEqual(len(self.client.get("/api/conversations").json()), 1)

    def test_individual_sources_add_retry_replace_failure_and_remove(self):
        with patch.object(api.indexer, "setup_embedding_model", side_effect=self.embedding), \
                patch.object(api.ollama, "create_llm", return_value=MockLLM()):
            def upload(name, data):
                return self.client.post("/api/upload", files=[("files", (name, data, "text/plain"))]).json()
            first = upload("first.txt", b"First document with the approval code CEDAR.")["sources"][0]
            added = upload("second.txt", b"Second document is about the ocean.")
            self.assertEqual(len(added["sources"]), 2)
            first_id = first["id"]
            self.client.post(f"/api/sources/{first_id}/retry").raise_for_status()
            original_engine = self.state["query_engine"]
            with patch.object(api.indexer, "create_query_engine", side_effect=RuntimeError("Embedding offline")):
                response = self.client.put(f"/api/sources/{first_id}", files=[("files", ("replacement.txt", b"Replacement document", "text/plain"))])
            self.assertEqual(response.status_code, 400)
            self.assertIs(self.state["query_engine"], original_engine)
            self.assertEqual(next(s for s in self.state["sources"] if s["id"] == first_id)["name"], "first.txt")
            replaced = self.client.put(f"/api/sources/{first_id}", files=[("files", ("replacement.txt", b"Replacement document", "text/plain"))]).json()
            self.assertEqual({s["name"] for s in replaced["sources"]}, {"replacement.txt", "second.txt"})
            failed = upload("empty.txt", b"")
            empty = next(s for s in failed["sources"] if s["status"] == "error")
            self.assertEqual(self.client.post(f"/api/sources/{empty['id']}/retry").status_code, 400)
            repaired = self.client.put(f"/api/sources/{empty['id']}", files=[("files", ("fixed.txt", b"A readable document", "text/plain"))]).json()
            self.assertTrue(all(s["status"] == "ready" for s in repaired["sources"]))
            removed = self.client.delete(f"/api/sources/{first_id}").json()
            self.assertEqual(len(removed["sources"]), 2)
            self.assertTrue(removed["has_index"])
            self.assertNotIn(first_id, self.state["source_inputs"])
            self.assertEqual(self.client.delete("/api/sources/not-owned").status_code, 404)

    def test_stop_saves_partial_answer_and_regenerate_replaces_one_turn(self):
        started, release, closed = threading.Event(), threading.Event(), threading.Event()
        def chunks(*args):
            try:
                yield "Partial"
                started.set()
                release.wait(5)
                yield " unwanted"
            finally:
                closed.set()
        results = []
        with patch.object(api.ollama, "chat", side_effect=chunks):
            thread = threading.Thread(target=lambda: results.append(self.client.post("/api/chat", json={"text": "Hello", "without_documents": True})))
            thread.start()
            try:
                self.assertTrue(started.wait(5))
                self.client.post("/api/chat/stop").raise_for_status()
                self.assertEqual(self.client.post("/api/conversations").status_code, 409)
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertTrue(closed.is_set())
        stopped = self.client.get("/api/state").json()["messages"][-1]
        self.assertTrue(stopped["stopped"])
        self.assertEqual(stopped["content"], "Partial")
        with patch.object(api.ollama, "chat", return_value=iter(["Complete answer"])):
            self.client.post("/api/chat", json={"text": "ignored", "regenerate": True}).raise_for_status()
        messages = self.client.get("/api/state").json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "Hello")
        self.assertTrue(messages[0]["without_documents"])
        self.assertEqual(messages[1]["content"], "Complete answer")

    def test_citations_keep_reader_page_metadata(self):
        from llama_index.core.schema import Document
        with patch.object(api.indexer, "setup_embedding_model", side_effect=self.embedding), \
                patch.object(api.ollama, "create_llm", return_value=MockLLM()):
            with api.operation(self.state):
                docs = api.tag_documents([Document(text="The approval code is ORBIT-7429.", metadata={"file_name": "report.pdf", "page_label": "7"})], "page-source", "file")
                api.commit_documents(self.state, docs)
        llm = Mock()
        llm.stream_chat.return_value = iter([SimpleNamespace(delta="ORBIT-7429 [1]")])
        with patch.object(api.ollama, "create_llm", return_value=llm):
            response = self.client.post("/api/chat", json={"text": "What is the approval code?"})
        source = json.loads(response.text.splitlines()[-1])["message"]["sources"][0]
        self.assertEqual(source["page"], "7")
        self.assertEqual(source["source_id"], "page-source")

    def test_remote_individual_controls_preserve_other_ids_on_failure(self):
        self.state["config"].r2r = True
        created = []
        def upload(paths, ids):
            document_id = f"owned-{len(created)}"
            created.append(document_id)
            ids.append(document_id)
            return ids
        with patch.object(api.R2RClient, "upload_documents", side_effect=upload), \
                patch.object(api.R2RClient, "delete_documents", return_value=[]) as delete:
            for name in ("one.txt", "two.txt"):
                self.client.post("/api/upload", files=[("files", (name, b"Remote text", "text/plain"))]).raise_for_status()
            first = self.state["sources"][0]
            self.assertEqual(len(self.state["r2r_document_ids"]), 2)
            delete.side_effect = [[first["remote_id"]], []]
            response = self.client.put(f"/api/sources/{first['id']}", files=[("files", ("new.txt", b"New text", "text/plain"))])
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.state["sources"][0], first)
            self.assertEqual(self.state["r2r_document_ids"], ["owned-0", "owned-1"])
            delete.side_effect = None
            self.client.delete(f"/api/sources/{first['id']}").raise_for_status()
            self.assertEqual(self.state["r2r_document_ids"], ["owned-1"])
            self.assertEqual(self.state["sources"][0]["name"], "two.txt")


if __name__ == "__main__":
    unittest.main()
