"""Offline regressions for retrieval boundaries and independent user sessions."""

import socket
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import Document, NodeWithScore, TextNode

from components.page_state import perform_project_reset
from utils import helpers, llama_index as rag, ollama, session_workspace as workspace
from utils import rag_pipeline as pipeline


class RetrievalBoundaryTests(unittest.TestCase):
    def retrieve(self, texts, question, scores=None, **settings):
        nodes = [TextNode(text=text, metadata={"file_name": f"file-{i}.txt"}) for i, text in enumerate(texts)]
        lookup = {node.node_id: node for node in nodes}
        vector = Mock()
        vector.retrieve.return_value = [NodeWithScore(node=nodes[i], score=value) for i, value in (scores or {}).items()]
        store = Mock()
        store.get_node.side_effect = lookup.__getitem__
        with patch.object(rag, "st", SimpleNamespace(session_state=settings)):
            retriever = rag.HybridRetriever(vector, store, list(lookup), top_k=3)
            results = retriever.retrieve(question)
        return results, vector, nodes

    def test_keyword_only_match_survives_and_vector_receives_original_question(self):
        question = "Where is ORBIT-7429?"
        results, vector, _ = self.retrieve(["Launch approval ORBIT-7429", "Unrelated cafeteria hours"], question)
        self.assertEqual(len(results), 1)
        self.assertIn("ORBIT-7429", results[0].node.text)
        vector.retrieve.assert_called_once_with(question)

    def test_single_document_common_word_and_single_digit_are_searchable(self):
        for question in ("refund", "7"):
            with self.subTest(question=question):
                results, _, _ = self.retrieve(["The refund approval code is 7."], question)
                self.assertEqual(len(results), 1)

    def test_empty_token_corpus_does_not_crash(self):
        results, _, _ = self.retrieve(["!!!"], "quantum physics")
        self.assertEqual(results, [])

    def test_summary_of_named_topic_never_adds_unrelated_introductions(self):
        results, _, _ = self.retrieve(["Orchard apple cultivation guide", "Refund policy allows returns"], "Summarize refund policy")
        self.assertEqual(len(results), 1)
        self.assertIn("Refund", results[0].node.text)
        results, _, _ = self.retrieve(["Orchard apple cultivation guide"], "Summarize quantum physics")
        self.assertEqual(results, [])

    def test_generic_summary_uses_openings_within_top_k(self):
        results, _, _ = self.retrieve(["First document", "Second document"], "Summarize my documents", top_k=1)
        self.assertEqual(len(results), 1)

    def test_large_chunk_cannot_exceed_budget_or_mutate_stored_evidence(self):
        text = "Relevant content " * 2000
        results, _, nodes = self.retrieve([text], "Relevant", {0: 0.9})
        self.assertLessEqual(sum(len(item.node.text) + 16 for item in results), rag.CONTEXT_CHAR_BUDGET)
        self.assertEqual(nodes[0].text, text)

    def test_nonfitting_middle_chunk_does_not_hide_smaller_candidates(self):
        results, _, _ = self.retrieve(["alpha " * 200, "beta " * 850, "small gamma"], "query", {0: .9, 1: .8, 2: .7})
        self.assertEqual(len(results), 2)
        self.assertIn("gamma", results[-1].node.text)


class SessionIsolationTests(unittest.TestCase):
    def test_pipeline_records_which_source_owns_the_active_index(self):
        state = {}
        try:
            for source in ("file_ingestion_stages", "website_ingestion_stages", "github_ingestion_stages"):
                with self.subTest(source=source), patch.object(pipeline, "st", SimpleNamespace(session_state=state)), \
                        patch.object(workspace, "st", SimpleNamespace(session_state=state)), \
                        patch.object(pipeline, "_rag_pipeline", return_value=None):
                    pipeline.rag_pipeline(status_state_key=source)
                    self.assertEqual(state["active_ingestion_source"], source)
        finally:
            workspace.clear_session_workspace(state)

    def test_failed_import_cleans_its_files_and_invalidates_old_corpus(self):
        state = {"query_engine": object(), "retriever": object(), "documents": ["old"]}
        try:
            parent = workspace.session_directory("data", state)
            sibling = parent / "unrelated.txt"
            sibling.write_text("KEEP")
            def fail(*args):
                (Path(args[-1]) / "upload.txt").write_text("PRIVATE")
                raise RuntimeError("test import failure")
            with patch.object(pipeline, "st", SimpleNamespace(session_state=state)), \
                    patch.object(workspace, "st", SimpleNamespace(session_state=state)), \
                    patch.object(pipeline, "_rag_pipeline", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "test import failure"):
                    pipeline.rag_pipeline()
            self.assertEqual(list(parent.iterdir()), [sibling])
            self.assertIsNone(state["query_engine"])
            self.assertIsNone(state["retriever"])
        finally:
            workspace.clear_session_workspace(state)

    def test_query_engine_uses_explicit_session_chat_model(self):
        from llama_index.core.llms import MockLLM
        llm = MockLLM(max_tokens=32)
        state = {"llm": llm, "embedding_model": MockEmbedding(embed_dim=4),
                 "embedding_config": {"model": "mock", "chunk_size": 64, "chunk_overlap": 0}}
        try:
            with patch.object(rag, "st", SimpleNamespace(session_state=state)), \
                    patch.object(workspace, "st", SimpleNamespace(session_state=state)):
                engine = rag.create_query_engine([Document(text="Private local fact")])
                self.assertIs(engine._response_synthesizer._llm, llm)
                self.assertIsNotNone(state["retriever"])
        finally:
            workspace.clear_session_workspace(state)

    def test_two_concurrent_sessions_keep_models_indexes_and_cache_private(self):
        active = ContextVar("test_session")
        class UI:
            @property
            def session_state(self):
                return active.get()
        ui = UI()
        barrier = threading.Barrier(2)
        states = []
        def embedding(**kwargs):
            return MockEmbedding(embed_dim=int(kwargs["model_name"]), model_name=kwargs["model_name"])
        def run_session(dimension):
            state = {}
            active.set(state)
            states.append(state)
            rag.setup_embedding_model(str(dimension), chunk_size=64, chunk_overlap=0, ollama_endpoint=f"http://server-{dimension}:11434")
            barrier.wait(timeout=10)
            docs = [Document(text="Same words, separate private index", metadata={"file_name": "private.txt"})]
            index = rag.create_index(docs)
            directory = rag.index_cache_dir(docs)
            self.assertTrue(rag.persist_index_to_cache(index, directory))
            restored = rag.load_index_from_cache(directory)
            self.assertIsNotNone(restored)
            self.assertEqual(restored._embed_model.embed_dim, dimension)
            return directory, list(index.vector_store.data.embedding_dict.values())[0]
        try:
            with patch.object(rag, "st", ui), patch.object(ollama, "st", ui), patch.object(workspace, "st", ui), \
                    patch.object(rag, "verify_embedding_model", return_value=True), patch.object(rag, "OllamaEmbedding", side_effect=embedding):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    first, second = list(executor.map(run_session, [4, 8]))
                self.assertNotEqual(first[0], second[0])
                self.assertEqual([len(first[1]), len(second[1])], [4, 8])
                active.set(states[0])
                other = next(path for path in (first[0], second[0]) if not Path(path).is_relative_to(Path(states[0]["_workspace"].name)))
                self.assertIsNone(rag.load_index_from_cache(other))
        finally:
            for state in states:
                workspace.clear_session_workspace(state)

    def test_reset_removes_only_own_files_and_cache(self):
        first, second = {}, {}
        try:
            first_path = workspace.session_directory("data", first) / "same.txt"
            second_path = workspace.session_directory("data", second) / "same.txt"
            first_path.write_text("FIRST")
            second_path.write_text("SECOND")
            perform_project_reset(first)
            self.assertFalse(first_path.exists())
            self.assertEqual(second_path.read_text(), "SECOND")
        finally:
            workspace.clear_session_workspace(first)
            workspace.clear_session_workspace(second)

    def test_cache_key_includes_boundaries_sources_and_endpoint(self):
        state = {"embedding_config": {"model": "same", "endpoint": "http://one"}}
        with patch.object(rag, "st", SimpleNamespace(session_state=state)):
            self.assertNotEqual(rag.index_cache_key(["ab", "c"]), rag.index_cache_key(["a", "bc"]))
            first = Document(text="fact", metadata={"file_name": "first.txt"})
            second = Document(text="fact", metadata={"file_name": "second.txt"})
            self.assertNotEqual(rag.index_cache_key([first]), rag.index_cache_key([second]))
            original = rag.index_cache_key([first])
            state["embedding_config"]["endpoint"] = "http://two"
            self.assertNotEqual(original, rag.index_cache_key([first]))


class IngestionSecurityTests(unittest.TestCase):
    def test_nonpublic_shared_address_space_is_blocked(self):
        self.assertTrue(helpers._is_blocked_ip("100.64.0.1"))

    def test_public_https_text_is_returned_with_tls_hostname_check(self):
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        response = Mock(status=200, headers={"Content-Type": "text/html"})
        response.stream.return_value = iter([b"<p>PUBLIC-FACT</p>"])
        pool = Mock()
        pool.urlopen.return_value = response
        with patch.object(helpers.socket, "getaddrinfo", return_value=public) as dns, \
                patch.object(helpers.urllib3, "HTTPSConnectionPool", return_value=pool):
            documents = helpers.load_website_documents(["https://public.test/page"])
        dns.assert_called_once()
        self.assertIn("PUBLIC-FACT", documents[0].text)
        response.close.assert_called_once()

    def test_repository_dot_segments_never_reach_clone(self):
        with patch.object(helpers.subprocess, "run") as run:
            for value in ("../repo", "owner/..", "./repo", "owner/.", "https://github.com/../repo"):
                self.assertFalse(helpers.clone_github_repo(value))
            run.assert_not_called()

    def test_duplicate_names_device_names_and_false_reported_size_are_rejected(self):
        for name in ("CON.txt", "NUL.pdf", "COM1.docx", "LPT9.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                helpers.safe_uploaded_filename(name)
        upload = lambda name: SimpleNamespace(name=name, size=0, getbuffer=lambda: b"1234")
        with self.assertRaisesRegex(ValueError, "distinct names"):
            helpers.validate_uploaded_files([upload("a.txt"), upload("A.TXT")])
        with patch.object(helpers, "MAX_UPLOAD_FILE_BYTES", 2), self.assertRaisesRegex(ValueError, "per-file"):
            helpers.validate_uploaded_files([upload("a.txt")])

    def test_zip_expansion_is_checked_before_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.docx"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", "x" * 5000)
            with patch.object(helpers, "MAX_TOTAL_UPLOAD_BYTES", 1000):
                with self.assertRaisesRegex(ValueError, "extraction size limit"):
                    helpers.validate_document_archive(path)

    def test_explicit_file_outside_source_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "repo"
            source.mkdir()
            outside = Path(directory) / "private.txt"
            outside.write_text("PRIVATE")
            with self.assertRaisesRegex(ValueError, "outside the selected source"):
                rag.load_documents(str(source), input_files=[str(outside)])

    def test_https_connection_is_pinned_and_closed_on_redirect_to_private_ip(self):
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        response = Mock(status=302, headers={"Location": "https://internal.test/private"})
        pool = Mock()
        pool.urlopen.return_value = response
        with patch.object(helpers.socket, "getaddrinfo", side_effect=[public, private]) as dns, \
                patch.object(helpers.urllib3, "HTTPSConnectionPool", return_value=pool) as connect:
            with self.assertRaisesRegex(ValueError, "blocked network"):
                helpers.load_website_documents(["https://public.test/page"])
        self.assertEqual(dns.call_count, 2)
        connect.assert_called_once()
        self.assertEqual(connect.call_args.args[0], "93.184.216.34")
        self.assertEqual(connect.call_args.kwargs["server_hostname"], "public.test")
        self.assertEqual(connect.call_args.kwargs["assert_hostname"], "public.test")
        self.assertEqual(connect.call_args.kwargs["cert_reqs"], "CERT_REQUIRED")
        self.assertEqual(pool.urlopen.call_args.kwargs["headers"]["Host"], "public.test")
        response.close.assert_called_once()
        pool.close.assert_called_once()

    def test_oversized_web_response_closes_connection(self):
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        response = Mock(status=200, headers={"Content-Type": "text/plain"})
        response.stream.return_value = iter([b"too large"])
        pool = Mock()
        pool.urlopen.return_value = response
        with patch.object(helpers.socket, "getaddrinfo", return_value=public), \
                patch.object(helpers.urllib3, "HTTPSConnectionPool", return_value=pool), \
                patch.object(helpers, "MAX_WEBSITE_RESPONSE_BYTES", 2):
            with self.assertRaisesRegex(ValueError, "too large"):
                helpers.load_website_documents(["https://public.test/"])
        response.close.assert_called_once()
        pool.close.assert_called_once()


class GroundingTests(unittest.TestCase):
    def test_rag_budget_counts_unicode_and_reserves_the_answer(self):
        with patch.object(ollama, "st", SimpleNamespace(session_state={})):
            messages = ollama._build_rag_messages("Summarize", "漢字 and facts " * 5000, [], "Be helpful")
        tokens = sum(ollama._estimate_tokens(message.content) + 8 for message in messages)
        self.assertLessEqual(tokens + 512 + 128, 2048)

    def test_model_refusal_does_not_get_an_invented_citation(self):
        node = TextNode(text="Some retrieved facts", metadata={"file_name": "facts.txt"})
        retriever = Mock()
        retriever.retrieve.return_value = [NodeWithScore(node=node, score=.8)]
        llm = Mock()
        llm.stream_chat.return_value = [SimpleNamespace(delta="I could not find this information.")]
        state = {"retriever": retriever, "messages": [{"role": "user", "content": "OLD-PRIVATE-DOC"}], "rag_history_start": 1}
        with patch.object(ollama, "st", SimpleNamespace(session_state=state)), patch.object(ollama, "create_llm", return_value=llm):
            answer = "".join(ollama.context_chat("Question", Mock()))
        self.assertNotIn("(from [1])", answer)
        messages = llm.stream_chat.call_args.args[0]
        self.assertNotIn("OLD-PRIVATE-DOC", str(messages))
        self.assertIn("untrusted data", str(messages))


if __name__ == "__main__":
    unittest.main()
