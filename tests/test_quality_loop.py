"""The live-answer loop, driven by a mock embedding model and a stand-in chat model."""
import unittest
from unittest.mock import patch

from llama_index.core.embeddings import MockEmbedding

from evaluation import quality
from utils import runtime
from utils.helpers import ALLOWED_UPLOAD_EXTENSIONS


def quoting_chat(prompt, query_engine=None):
    """Stand-in model: quote the top retrieved passage and cite it, or refuse."""
    nodes = runtime.st.session_state["retriever"].retrieve(prompt)
    runtime.st.session_state["last_doc_sources"] = [(n.node.metadata.get("file_name"), n.score) for n in nodes]
    if not nodes:
        yield "I could not find this information in the documents."
        return
    yield nodes[0].node.get_content() + " (from [1])"


class LiveLoopTests(unittest.TestCase):
    def run_loop(self):
        def embedding(*_args, **_kwargs):
            model = MockEmbedding(embed_dim=8)
            runtime.st.session_state["embedding_model"] = model
            return model

        with patch("utils.ollama.verify_chat_model", return_value=True), \
                patch("utils.llama_index.setup_embedding_model", side_effect=embedding), \
                patch("utils.ollama.context_chat", side_effect=quoting_chat):
            return quality.evaluate_answers(False, "http://localhost:11434", "mock-embed", "mock-chat")

    def test_every_case_and_format_is_graded(self):
        results = self.run_loop()
        names = [r["test"] for r in results]
        expected = [c["name"] for c in quality.CASES] + ["format" + e for e in sorted(ALLOWED_UPLOAD_EXTENSIONS)]
        self.assertEqual(sorted(names), sorted(expected))
        by_name = {r["test"]: r for r in results}
        # A quoted, cited passage satisfies the exact-fact case.
        self.assertTrue(by_name["refund_days"]["pass"], by_name["refund_days"]["detail"])
        self.assertIn("(from [1])", by_name["refund_days"]["answer"])
        # Quoting a document that contains an injected instruction fails the forbidden-fact check.
        self.assertFalse(by_name["document_instruction_injection"]["pass"])
        for result in results:
            self.assertEqual(result["kind"], "live_answer")
            self.assertIn(result["status"], {"passed", "failed"})

    def test_unavailable_chat_model_is_an_error_not_a_skip(self):
        with patch("utils.ollama.verify_chat_model", return_value=False), \
                self.assertRaisesRegex(RuntimeError, "unavailable"):
            quality.evaluate_answers(False, "http://localhost:11434", "mock-embed", "missing-model")


if __name__ == "__main__":
    unittest.main()
