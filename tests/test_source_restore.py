"""Opt-in source persistence: saved only when enabled, restored after a restart, deleted on opt-out."""
import importlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM

from backend import source_store
from utils import runtime
from utils.session_workspace import clear_session_workspace

api = importlib.import_module("backend.app")
HEADERS = {"X-DocMind-Client": "react"}


class SourceRestoreTests(unittest.TestCase):
    def setUp(self):
        self.title_worker = patch("backend.workspace.start_title")
        self.title_worker.start()
        self.addCleanup(self.title_worker.stop)
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        db = patch.object(api.history, "DB_PATH", Path(self.storage.name) / "history.sqlite3")
        db.start()
        self.addCleanup(db.stop)
        self.client = TestClient(api.app, headers=HEADERS)
        self.addCleanup(self.close)
        self.client.post("/api/session").raise_for_status()

    def close(self):
        for state in list(api.sessions.values()):
            clear_session_workspace(state)
        api.sessions.clear()
        self.client.close()

    def embedding(self, *args):
        model = MockEmbedding(embed_dim=8)
        runtime.st.session_state["embedding_model"] = model
        runtime.st.session_state["embedding_config"] = {"model": "mock", "chunk_size": 256, "chunk_overlap": 32}
        return model

    def models(self, failing=False):
        side_effect = RuntimeError("Embedding server offline.") if failing else self.embedding
        return (patch.object(api.indexer, "setup_embedding_model", side_effect=side_effect),
                patch.object(api.ollama, "create_llm", return_value=MockLLM()))

    def enable(self, value=True):
        settings = self.client.get("/api/state").json()["settings"]
        response = self.client.put("/api/settings", json={**settings, "keep_sources": value})
        self.assertEqual(response.status_code, 200, response.text)

    def import_sample(self):
        embed, llm = self.models()
        with embed, llm:
            response = self.client.post("/api/import", json={"kind": "sample"})
        self.assertEqual(response.status_code, 200, response.text)

    def owner(self):
        return next(iter(api.sessions.values()))["owner"]

    def restart(self, failing=False):
        """Drop in-memory workspaces like a backend restart, reconnect, and wait for the restore."""
        for state in list(api.sessions.values()):
            clear_session_workspace(state)
        api.sessions.clear()
        embed, llm = self.models(failing)
        with embed, llm:
            first = self.client.post("/api/session").json()
            deadline = time.monotonic() + 30
            state = first
            while state["busy"] and time.monotonic() < deadline:
                time.sleep(0.05)
                state = self.client.get("/api/state").json()
        return first, state

    def test_sources_are_not_saved_by_default(self):
        self.import_sample()
        self.assertIsNone(source_store.load(self.owner()))
        _, state = self.restart()
        self.assertEqual(state["sources"], [])

    def test_opted_in_sources_survive_a_restart(self):
        self.enable()
        self.import_sample()
        self.assertIsNotNone(source_store.load(self.owner()))
        first, state = self.restart()
        self.assertTrue(first["sources"], "the restored list is visible while the index rebuilds")
        self.assertTrue(first["settings"]["keep_sources"])
        self.assertTrue(state["has_index"])
        self.assertEqual([s["status"] for s in state["sources"]], ["ready"])
        self.assertIn("November 12", state["sources"][0]["preview"])

    def test_restore_failure_marks_sources_for_retry(self):
        self.enable()
        self.import_sample()
        _, state = self.restart(failing=True)
        self.assertFalse(state["has_index"])
        self.assertEqual(state["sources"][0]["status"], "error")
        self.assertIn("Retry when the model server is available", state["sources"][0]["error"])
        embed, llm = self.models()
        with embed, llm:
            retried = self.client.post(f"/api/sources/{state['sources'][0]['id']}/retry")
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertTrue(retried.json()["has_index"])

    def test_opting_out_or_removing_sources_deletes_the_saved_copy(self):
        self.enable()
        self.import_sample()
        self.enable(False)
        self.assertIsNone(source_store.load(self.owner()))
        self.enable()
        self.assertIsNotNone(source_store.load(self.owner()))
        self.client.delete("/api/sources").raise_for_status()
        self.assertIsNone(source_store.load(self.owner()))

    def test_saved_copy_has_no_credentials(self):
        settings = self.client.get("/api/state").json()["settings"]
        self.client.put("/api/settings", json={**settings, "keep_sources": True, "api_key": "sk-test-not-real"})
        self.import_sample()
        raw = (Path(self.storage.name) / "sources" / f"{self.owner()}.json").read_text(encoding="utf-8")
        self.assertNotIn("sk-test-not-real", raw)
        self.assertNotIn("api_key", raw)


if __name__ == "__main__":
    unittest.main()
