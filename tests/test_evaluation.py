import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import eval_harness as evaluation
from eval_quality import grade_answer, evaluate_answers


class EvaluationTests(unittest.TestCase):
    def test_skips_and_exceptions_are_not_passes(self):
        results = []
        evaluation._check(results, "success", lambda: (True, "ok"))
        evaluation._check(results, "skip", Mock(side_effect=unittest.SkipTest("offline")))
        evaluation._check(results, "error", Mock(side_effect=RuntimeError("broken")))
        summary = evaluation.summarize_results("test", results)
        self.assertEqual((summary["passed"], summary["failed"], summary["skipped"]), (1, 1, 1))
        self.assertEqual(summary["score"], 0.5)

    def test_all_skipped_has_no_score(self):
        self.assertIsNone(evaluation.summarize_results("test", [{"pass": None}])["score"])

    def test_mock_mode_never_calls_real_model_or_passes_live_cases(self):
        with patch("utils.ollama.verify_chat_model", side_effect=AssertionError("network call")):
            results = evaluate_answers(True, "unused", "unused", "unused")
        self.assertEqual(len(results), 34)
        self.assertTrue(all(item["status"] == "skipped" and item["pass"] is None for item in results))

    def test_real_embedding_failure_cannot_fall_back_silently(self):
        with patch("utils.llama_index.setup_embedding_model", side_effect=RuntimeError("offline")):
            with self.assertRaisesRegex(RuntimeError, "Use --mock explicitly"):
                evaluation._try_real_embeddings("http://127.0.0.1:1", "missing")

    def test_citation_must_exist_and_point_to_expected_source(self):
        sources = [("wrong.txt", .9), ("refund.txt", .8)]
        for answer in ("30 days", "30 days [99]", "30 days [1]"):
            with self.subTest(answer=answer):
                self.assertFalse(all(grade_answer(answer, sources, required=[r"30 days"], expected_sources=["refund.txt"]).values()))
        self.assertTrue(all(grade_answer("30 days [2]", sources, required=[r"30 days"], expected_sources=["refund.txt"]).values()))

    def test_correct_citation_does_not_excuse_wrong_fact(self):
        checks = grade_answer("60 days [1]", [("refund.txt", .9)], required=[r"30 days"])
        self.assertTrue(checks["citations"])
        self.assertFalse(checks["required_facts"])

    def test_refusal_with_invented_answer_is_rejected(self):
        answer = "I could not find this information in the documents. The answer is Paris."
        self.assertFalse(all(grade_answer(answer, [], refusal=True).values()))

    def test_hash_embeddings_are_stable_across_processes(self):
        script = "import json,streamlit as st; from eval_harness import _setup_hash_embeddings; _setup_hash_embeddings(); print(json.dumps(st.session_state['embedding_model'].get_query_embedding('Refund policy 30 days')))"
        vectors = []
        for seed in ("1", "2"):
            result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                    env={**os.environ, "PYTHONHASHSEED": seed}, timeout=45, check=True)
            vectors.append(json.loads(result.stdout.strip().splitlines()[-1]))
        self.assertEqual(vectors[0], vectors[1])

    def test_report_keeps_skips_and_answers_visible(self):
        result = evaluation.summarize_results("generation", [{"test": "live", "pass": None, "status": "skipped", "answer": "", "detail": "offline"}])
        overall = {"passed": 0, "failed": 0, "skipped": 1, "mode": "mock", "chat_model": None, "embedding_model": "hash-mock"}
        with tempfile.TemporaryDirectory() as directory:
            paths = evaluation._write_outputs({"generation": result}, overall, Path(directory) / "new")
            self.assertIn("SKIPPED", paths[1].read_text(encoding="utf-8"))
            self.assertIsNone(json.loads(paths[0].read_text())["suites"]["generation"]["score"])

    def test_money_back_phrase_retrieves_refunds_without_expanding_back_alone(self):
        from llama_index.core.schema import TextNode
        from utils import llama_index as rag

        node = TextNode(text="Refunds are available within 30 days.")
        store = Mock()
        store.get_node.return_value = node
        vector = Mock()
        vector.retrieve.return_value = []
        with patch.object(rag, "st", SimpleNamespace(session_state={})):
            retriever = rag.HybridRetriever(vector, store, [node.node_id], 3)
            self.assertTrue(retriever.retrieve("money back rules"))
            self.assertEqual(retriever.retrieve("back pain"), [])

    def test_missing_evidence_returns_without_creating_a_model(self):
        from utils import ollama

        retriever = Mock()
        retriever.retrieve.return_value = []
        state = {"retriever": retriever}
        with patch.object(ollama, "st", SimpleNamespace(session_state=state)), patch.object(
            ollama, "create_llm", side_effect=AssertionError("must not initialize")
        ) as create:
            answer = "".join(ollama.context_chat("missing fact", query_engine=None))
        self.assertEqual(answer, "I could not find this information in the documents.")
        create.assert_not_called()

    def test_invalid_citation_is_flagged_without_fabricating_a_replacement(self):
        from llama_index.core.schema import TextNode, NodeWithScore
        from utils import ollama

        retriever = Mock()
        retriever.retrieve.return_value = [NodeWithScore(node=TextNode(text="Refunds take 30 days", metadata={"file_name": "refund.txt"}), score=.9)]
        llm = Mock()
        llm.stream_chat.return_value = [SimpleNamespace(delta="30 days ["), SimpleNamespace(delta="9]")]
        state = {"retriever": retriever, "selected_model": "test", "ollama_endpoint": "http://localhost:11434"}
        with patch.object(ollama, "st", SimpleNamespace(session_state=state)), patch.object(ollama, "create_llm", return_value=llm):
            answer = "".join(ollama.context_chat("When?", query_engine=None))
        self.assertIn("invalid source reference", answer)
        self.assertIn("[9]", answer)
        self.assertNotIn("[1]", answer)

    def test_xml_retains_field_names_and_attributes(self):
        from utils.document_readers import DocumentTextReader

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "launch.xml"
            path.write_text('<launch status="approved"><code>ORBIT-7429</code></launch>')
            text = DocumentTextReader().load_data(path)[0].text
        for expected in ("launch", "status", "approved", "code", "ORBIT-7429"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
