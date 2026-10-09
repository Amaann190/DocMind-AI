"""Real Streamlit widget reruns plus backend failure/ownership regressions."""
import io
import json
import httpx
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from docx import Document
from streamlit.testing.v1 import AppTest

from components import chatbox as chat_ui
from components.page_state import perform_project_reset
from components.tabs.settings import chat_history_docx, _chat_history_signature
from utils import ollama, r2r
from utils.browser_settings import apply_persisted_settings

ROOT = Path(__file__).resolve().parents[1]


class UserWorkflowTests(unittest.TestCase):
    def app(self, **state):
        app = AppTest.from_file(str(ROOT / "main.py"), default_timeout=30)
        defaults = dict(browser_settings_restored=True, ollama_endpoint="http://localhost:11434",
                        ollama_models=["llama3:latest"], ollama_embedding_models=["nomic-embed-text:latest"],
                        ollama_models_endpoint="http://localhost:11434",
                        ollama_embedding_models_endpoint="http://localhost:11434")
        defaults.update(state)
        for key, value in defaults.items():
            app.session_state[key] = value
        return app.run()

    def assert_clean(self, app):
        self.assertEqual(list(app.exception), [])

    def test_advanced_settings_and_provider_switches_survive_real_widget_reruns(self):
        app = self.app()
        app.toggle(key="advanced").set_value(True).run()
        self.assert_clean(app)
        app.number_input(key="chunk_size").set_value(512).run()
        self.assertEqual(app.session_state["chunk_overlap"], 61)
        for backend in ("LM Studio (Local AI)", "TabbyAPI", "OpenAI", "Ollama"):
            app.selectbox(key="llm_backend").select(backend).run()
            self.assert_clean(app)
            self.assertEqual(app.session_state["llm_backend"], backend)

    def test_fallback_button_survives_rerun_and_calls_general_chat(self):
        def no_evidence(prompt, query_engine):
            import streamlit as st
            st.session_state.update(last_rag_no_result=True, last_rag_question=prompt)
            yield "I could not find this information in the documents."
        with patch.object(chat_ui, "context_chat", side_effect=no_evidence), patch.object(
            chat_ui, "chat", return_value=iter(["General answer"])) as general:
            app = self.app(query_engine=object())
            app.chat_input[0].set_value("Missing fact?").run()
            app.run()
            app.button(key="ask_without_docs_btn").click().run()
            self.assert_clean(app)
            general.assert_called_once_with(prompt="Missing fact?")
            self.assertEqual(app.session_state["messages"][-1]["content"], "General answer")

    def test_sources_survive_rerender_and_word_export(self):
        def answer(prompt, query_engine):
            import streamlit as st
            st.session_state["last_doc_sources"] = [("a.txt", .9), ("a.txt", .8), ("b.txt", .7)]
            yield "A fact [3]"
        with patch.object(chat_ui, "context_chat", side_effect=answer):
            app = self.app(query_engine=object())
            app.chat_input[0].set_value("Which fact?").run()
            app.run()
            self.assert_clean(app)
            self.assertTrue(any("[3] b.txt" in item.value for item in app.caption))
            document = Document(io.BytesIO(chat_history_docx(_chat_history_signature(app.session_state["messages"]))))
            self.assertIn("Source [3]: b.txt", "\n".join(p.text for p in document.paragraphs))

    def test_interrupted_response_keeps_partial_answer_and_allows_next_turn(self):
        def broken(prompt):
            yield "Partial answer"
            raise ConnectionError("disconnected")
        with patch.object(chat_ui, "chat", side_effect=broken):
            app = self.app()
            app.chat_input[0].set_value("Hello").run()
            self.assert_clean(app)
            self.assertIn("Partial answer", app.session_state["messages"][-1]["content"])
            self.assertIn("interrupted", app.session_state["messages"][-1]["content"])
        with patch.object(chat_ui, "chat", return_value=iter(["Recovered"])):
            app.chat_input[0].set_value("Try again").run()
            self.assertEqual(app.session_state["messages"][-1]["content"], "Recovered")

    def test_r2r_chat_does_not_require_local_models_and_wrong_server_is_blocked(self):
        with patch("components.page_state.get_models", return_value=[]), patch(
            "components.page_state.get_embedding_models", return_value=[]), patch.object(
            r2r, "r2r_chat", return_value=iter(["Remote answer"])) as remote:
            app = self.app(r2r_enabled=True, r2r_document_ids=["owned"],
                           r2r_document_origin={"base_url": "http://localhost:7272", "api_key": ""},
                           ollama_models=[], ollama_embedding_models=[])
            app.chat_input[0].set_value("Remote question").run()
            self.assert_clean(app)
            remote.assert_called_once()
            app.text_input(key="r2r_base_url").set_value("http://localhost:7273").run()
            app.chat_input[0].set_value("Wrong server?").run()
            remote.assert_called_once()
            self.assertTrue(any("no ready documents" in w.value for w in app.warning))

    def test_reset_clears_credentials_inputs_and_fallback(self):
        state = dict(openai_api_key="secret", r2r_api_key="secret", r2r_enabled=True,
                     websites=["https://example.test"], github_repo="owner/repo",
                     last_rag_no_result=True, last_rag_question="old", similarity_cutoff=.9)
        self.assertTrue(perform_project_reset(state))
        self.assertFalse(state["openai_api_key"] or state["r2r_api_key"] or state["r2r_enabled"])
        self.assertEqual(state["websites"], [])
        self.assertFalse(state["github_repo"] or state["last_rag_no_result"])
        self.assertEqual(state["similarity_cutoff"], .3)
        self.assertEqual(state["upload_epoch"], 1)

    def test_failed_import_keeps_settings_accessible_and_waits_for_explicit_retry(self):
        upload = io.BytesIO(b"The approval code is ORBIT-7429.")
        upload.name, upload.size, upload.type = "fact.txt", len(upload.getvalue()), "text/plain"
        with patch("streamlit.file_uploader", return_value=[upload]), patch.object(
            ollama, "verify_chat_model", return_value=False) as verify:
            app = self.app()
            self.assert_clean(app)
            self.assertEqual(app.selectbox(key="llm_backend").value, "Ollama")
            verify.assert_called_once()
            app.run()
            verify.assert_called_once()
            app.button(key="reprocess_files").click().run()
            self.assertEqual(verify.call_count, 2)
            self.assertIsNone(app.session_state["query_engine"])
            app.session_state["_workspace"].cleanup()

    def test_partial_import_warning_survives_a_full_widget_rerun(self):
        from llama_index.core.embeddings import MockEmbedding
        from llama_index.core.llms import MockLLM
        uploads = []
        for name, data in (("fact.txt", b"The approval code is ORBIT-7429."), ("empty.txt", b"")):
            item = io.BytesIO(data)
            item.name, item.size, item.type = name, len(data), "text/plain"
            uploads.append(item)
        embedding = MockEmbedding(embed_dim=8)
        with patch("streamlit.file_uploader", return_value=uploads), patch.object(
            ollama, "verify_chat_model", return_value=True), patch.object(
            ollama, "create_llm", return_value=MockLLM()), patch(
            "utils.llama_index.setup_embedding_model", return_value=embedding):
            app = self.app(embedding_model=embedding)
            self.assert_clean(app)
            self.assertIsNotNone(app.session_state["query_engine"])
            app.run()
            self.assertTrue(any("1 file(s)" in item.value for item in app.warning))
            self.assertTrue(any("empty.txt" in item.value for item in app.text))
            app.session_state["_workspace"].cleanup()

    def test_reset_button_and_clear_chat_work_on_real_reruns(self):
        app = self.app(messages=[{"role": "user", "content": "old"}], rag_history_start=50, chat_history_start=50,
                       github_repo="owner/repo", websites=["https://public.test"], advanced=True)
        next(button for button in app.button if button.label == "💬 Clear Chat").click().run()
        self.assertEqual(app.session_state["rag_history_start"], 0)
        self.assertEqual(app.session_state["chat_history_start"], 0)
        app.checkbox(key="confirm_project_reset").check().run()
        with patch("components.page_state.get_models", return_value=["llama3:latest"]), patch(
            "components.page_state.get_embedding_models", return_value=["nomic-embed-text:latest"]):
            next(button for button in app.button if button.label == "Yes, reset everything").click().run()
        self.assert_clean(app)
        self.assertEqual(app.session_state["websites"], [])
        self.assertFalse(app.session_state["advanced"])
        self.assertEqual(app.session_state["upload_epoch"], 1)
        self.assertEqual(app.session_state["chat_history_start"], 0)

    def test_removing_all_uploads_detaches_index_and_old_chat_then_allows_reupload(self):
        from llama_index.core.embeddings import MockEmbedding
        from llama_index.core.llms import MockLLM
        item = io.BytesIO(b"The approval code is ORBIT-7429.")
        item.name, item.size, item.type = "fact.txt", len(item.getvalue()), "text/plain"
        embedding = MockEmbedding(embed_dim=8)
        with patch("streamlit.file_uploader", return_value=[item]) as uploader, patch.object(
            ollama, "verify_chat_model", return_value=True), patch.object(
            ollama, "create_llm", return_value=MockLLM()) as create_llm, patch(
            "utils.llama_index.setup_embedding_model", return_value=embedding):
            app = self.app(embedding_model=embedding)
            try:
                self.assertIsNotNone(app.session_state["query_engine"])
                app.session_state["messages"] = [
                    {"role": "user", "content": "What is the approval code?"},
                    {"role": "assistant", "content": "ORBIT-7429", "sources": [("fact.txt", .9)]},
                ]
                uploader.return_value = []
                app.run()
                self.assert_clean(app)
                for key in ("query_engine", "retriever", "documents", "processed_file_signature"):
                    self.assertIsNone(app.session_state[key])
                self.assertEqual(app.session_state["file_list"], [])
                self.assertEqual(app.session_state["file_ingestion_stages"], [])
                self.assertEqual(len(app.session_state["messages"]), 2)
                self.assertTrue(any("Chat Mode" in item.value for item in app.info))

                client = Mock()
                client.stream_chat.return_value = iter([SimpleNamespace(delta="No document context.")])
                create_llm.return_value = client
                app.chat_input[0].set_value("What was that code?").run()
                self.assert_clean(app)
                sent = client.stream_chat.call_args.args[0]
                self.assertNotIn("ORBIT-7429", " ".join(message.content for message in sent))
                self.assertEqual(sent[-1].content, "What was that code?")

                create_llm.return_value = MockLLM()
                uploader.return_value = [item]
                app.run()
                self.assert_clean(app)
                self.assertIsNotNone(app.session_state["query_engine"])
            finally:
                app.session_state["_workspace"].cleanup()

    def test_removing_uploads_preserves_active_website_or_repository(self):
        for source in ("website_ingestion_stages", "github_ingestion_stages"):
            with self.subTest(source=source), patch("streamlit.file_uploader", return_value=[]):
                engine, retriever = object(), object()
                app = self.app(active_ingestion_source=source, query_engine=engine,
                    retriever=retriever, documents=["other source"], file_list=["old.txt"],
                    processed_file_signature=("old",), rag_history_start=1)
                self.assert_clean(app)
                self.assertIs(app.session_state["query_engine"], engine)
                self.assertIs(app.session_state["retriever"], retriever)
                self.assertEqual(app.session_state["documents"], ["other source"])
                self.assertEqual(app.session_state["rag_history_start"], 1)
                self.assertEqual(app.session_state["file_list"], [])

    def test_removing_remote_uploads_blocks_queries_but_retains_cleanup_ownership(self):
        origin = {"base_url": "http://localhost:7272", "api_key": ""}
        with patch("streamlit.file_uploader", return_value=[]), patch.object(r2r, "r2r_chat") as remote:
            app = self.app(active_ingestion_source="file_ingestion_stages", file_list=["old.txt"],
                r2r_enabled=True, r2r_document_ids=["owned"], r2r_document_origin=origin)
            app.chat_input[0].set_value("What was in the removed file?").run()
            self.assert_clean(app)
            remote.assert_not_called()
            self.assertEqual(app.session_state["r2r_document_ids"], ["owned"])
            self.assertEqual(app.session_state["r2r_document_origin"], origin)
            self.assertTrue(app.session_state["r2r_ingestion_failed"])

    def test_invalid_persisted_values_do_not_crash_widgets(self):
        state = {}
        apply_persisted_settings(state, {"top_k": 999, "temperature": "nan", "chunk_size": -1,
                                         "llm_backend": "unknown", "answer_style": "unknown"})
        self.assertEqual(state, {})

    def test_compatible_custom_model_metadata_and_temperature_are_current(self):
        for backend in ("OpenAI", "LM Studio (Local AI)", "TabbyAPI"):
            for temperature in (.1, 1.2):
                with patch.object(ollama, "st", SimpleNamespace(session_state={"llm_backend": backend, "temperature": temperature})):
                    model = ollama.create_llm("my-local-model", "http://localhost:1234/v1")
                    self.assertEqual(model.metadata.model_name, "my-local-model")
                    self.assertTrue(model.metadata.is_chat_model)
                    self.assertEqual(model.temperature, temperature)

    def test_custom_model_stream_uses_real_compatible_transport(self):
        from llama_index.core.llms import ChatMessage, MessageRole
        def respond(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "my-local-model")
            self.assertTrue(payload["stream"])
            self.assertEqual(request.url.path, "/v1/chat/completions")
            event = {"id": "test", "created": 1, "model": "my-local-model", "object": "chat.completion.chunk",
                     "choices": [{"index": 0, "delta": {"role": "assistant", "content": "READY"}, "finish_reason": None}]}
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  text="data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n")
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            model = ollama.CompatibleChatLLM(model="my-local-model", api_key="test",
                api_base="http://local.test/v1", http_client=client, max_tokens=32, max_retries=0)
            answer = "".join(chunk.delta or "" for chunk in model.stream_chat([
                ChatMessage(role=MessageRole.USER, content="Hello")]))
        self.assertEqual(answer, "READY")

    def test_r2r_failed_cleanup_retains_ids_and_original_connection(self):
        origin = {"base_url": "http://original:7272", "api_key": "original-key"}
        state = dict(r2r_document_ids=["owned"], r2r_document_origin=origin,
                     r2r_base_url="http://different:7272", messages=[{"content": "keep"}])
        with patch.object(r2r, "R2RClient") as client:
            client.return_value.delete_documents.return_value = ["owned"]
            self.assertFalse(perform_project_reset(state))
            client.assert_called_once_with(**origin)
            self.assertEqual(state["r2r_document_ids"], ["owned"])
            self.assertEqual(state["messages"], [{"content": "keep"}])
            client.return_value.delete_documents.return_value = []
            self.assertTrue(perform_project_reset(state))

    def test_r2r_upload_contract_and_partial_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.txt"
            path.write_text("fact")
            response = Mock()
            response.json.return_value = {"results": {"document_id": "owned"}}
            client = r2r.R2RClient()
            ids = []
            with patch.object(client, "_request", side_effect=[response, r2r.R2RConnectionError("failed")]) as request, patch.object(r2r, "uuid4", side_effect=["owned", "pending"]):
                with self.assertRaises(r2r.R2RConnectionError):
                    client.upload_documents([path, path], ids)
                self.assertEqual(ids, ["owned", "pending"])
                self.assertIn("file", request.call_args_list[0].kwargs["files"])
                self.assertEqual(request.call_args_list[0].kwargs["data"]["run_with_orchestration"], "false")
        with patch.object(client, "_request") as request:
            with self.assertRaises(r2r.R2RConnectionError):
                client.rag("unscoped")
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
