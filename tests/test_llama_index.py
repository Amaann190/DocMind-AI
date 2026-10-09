import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import Document, NodeWithScore, TextNode

from utils.llama_index import (
    HybridRetriever,
    OllamaEmbedding,
    _bm25_expanded_tokens,
    _bm25_tokens,
    _context_char_budget,
    _dedupe_exact_nodes,
    _document_title,
    _prepend_document_title,
    _rewrite_query,
    setup_embedding_model,
    verify_embedding_model,
)


class _FakeOpenAIEmbedding(BaseEmbedding):
    """Stand-in OpenAIEmbedding that records its constructor kwargs."""

    def __init__(self, **kwargs):
        super().__init__()
        object.__setattr__(self, "kwargs", kwargs)

    def _get_query_embedding(self, query):
        return [0.0]

    async def _aget_query_embedding(self, query):
        return [0.0]

    def _get_text_embedding(self, text):
        return [0.0]


class _FakeOllamaClient:
    def __init__(self, host, timeout=30):
        self.host = host

    def list(self):
        return {
            "models": [
                {"model": "nomic-embed-text:latest"},
                {"model": "qwen2.5:0.5b"},
            ]
        }

    def show(self, model_name):
        if model_name == "nomic-embed-text:latest":
            return {"capabilities": ["embedding"]}
        return {"capabilities": ["completion"]}


class EmbeddingModelValidationTests(unittest.TestCase):
    def test_verify_embedding_model_accepts_installed_embedding_model(self):
        with patch("utils.llama_index.ollama.Client", _FakeOllamaClient):
            self.assertTrue(
                verify_embedding_model(
                    "nomic-embed-text:latest", "http://localhost:11434"
                )
            )

    def test_verify_embedding_model_rejects_missing_model(self):
        with patch("utils.llama_index.ollama.Client", _FakeOllamaClient):
            self.assertFalse(
                verify_embedding_model("missing:latest", "http://localhost:11434")
            )

    def test_verify_embedding_model_rejects_non_embedding_model(self):
        with patch("utils.llama_index.ollama.Client", _FakeOllamaClient):
            self.assertFalse(
                verify_embedding_model("qwen2.5:0.5b", "http://localhost:11434")
            )

    def test_verify_embedding_model_false_when_server_down(self):
        with patch(
            "utils.llama_index.ollama.Client", side_effect=RuntimeError("boom")
        ):
            self.assertFalse(
                verify_embedding_model("nomic-embed-text:latest", "http://localhost:11434")
            )

    def test_setup_embedding_model_raises_for_missing_model(self):
        with patch("utils.llama_index.ollama.Client", _FakeOllamaClient):
            with self.assertRaises(ValueError) as context:
                setup_embedding_model(
                    "missing:latest", ollama_endpoint="http://localhost:11434"
                )
        self.assertIn("missing:latest", str(context.exception))

    def test_setup_embedding_model_uses_openai_backend(self):
        with patch(
            "llama_index.embeddings.openai.OpenAIEmbedding",
            _FakeOpenAIEmbedding,
        ):
            embedding = setup_embedding_model(
                "text-embedding-3-small",
                chunk_size=128,
                chunk_overlap=16,
                backend="OpenAI",
                ollama_endpoint="http://localhost:1234/v1",
                api_key="secret",
            )
        self.assertEqual(embedding.kwargs["model_name"], "text-embedding-3-small")
        self.assertEqual(embedding.kwargs["api_key"], "secret")
        self.assertEqual(embedding.kwargs["api_base"], "http://localhost:1234/v1")
        self.assertEqual(embedding.kwargs["embed_batch_size"], 16)


class _OomFakeClient:
    """Embed client that fails once on full-size batches, then succeeds."""

    def __init__(self, host, timeout=300):
        self.host = host
        self.calls = []

    def embed(self, model, input):
        self.calls.append(len(input))
        if self.calls[-1] == 8:
            raise RuntimeError("CUDA out of memory")
        return SimpleNamespace(embeddings=[[0.1] * 4 for _ in input])


class OllamaEmbeddingTests(unittest.TestCase):
    def _embedding(self, client):
        embedding = OllamaEmbedding(
            model_name="nomic-embed-text:latest",
            base_url="http://localhost:11434",
        )
        embedding.embed_batch_size = 8
        embedding._client = client
        return embedding

    def test_batch_shrinks_and_recovers_after_oom(self):
        client = _OomFakeClient("http://localhost:11434")
        embedding = self._embedding(client)
        texts = [f"text {i}" for i in range(20)]

        result = embedding.get_text_embedding_batch(texts)

        self.assertEqual(len(result), 20)
        self.assertEqual(client.calls[0], 8)
        self.assertEqual(client.calls[1], 4)
        self.assertEqual(embedding.embed_batch_size, 4)
        self.assertTrue(all(call <= 4 for call in client.calls[2:]))

    def test_single_item_failure_raises(self):
        client = _OomFakeClient("http://localhost:11434")

        def always_fail(model, input):
            raise RuntimeError("boom")

        client.embed = always_fail
        embedding = self._embedding(client)

        with self.assertRaises(RuntimeError):
            embedding.get_text_embedding_batch(["a", "b"])


class QueryUnderstandingTests(unittest.TestCase):
    def test_bm25_tokens_are_stemmed(self):
        self.assertEqual(_bm25_tokens("Running documents quickly"), ["run", "document", "quickli"])

    def test_bm25_tokens_split_hyphens_and_drop_single_letters(self):
        self.assertEqual(
            _bm25_tokens("30-day money-back guarantee's"),
            ["30", "day", "money", "back", "guarante"],
        )

    def test_bm25_expansion_adds_synonyms_to_short_queries(self):
        expanded = _bm25_expanded_tokens(["refund", "polici"])
        self.assertIn("return", expanded)
        self.assertIn("rule", expanded)
        self.assertIn("refund", expanded)

    def test_bm25_expansion_leaves_long_queries_untouched(self):
        tokens = ["very", "specific", "long", "technical", "query"]
        self.assertEqual(_bm25_expanded_tokens(tokens), tokens)

    def test_document_title_from_filename(self):
        node = TextNode(text="body", metadata={"file_name": "annual_report.md"})
        self.assertEqual(_document_title(node), "Annual Report")

    def test_prepend_document_title_prefixes_chunks_once(self):
        node = TextNode(
            text="The company grew revenues by 12 percent.",
            metadata={"file_name": "annual_report.md"},
        )
        _prepend_document_title([node])
        self.assertTrue(node.get_content().startswith("Annual Report.\n\n"))
        _prepend_document_title([node])
        self.assertTrue(node.get_content().startswith("Annual Report.\n\n"))

    def test_rewrite_query_stems_and_drops_fillers(self):
        rewritten = _rewrite_query("Tell me about the running documents")
        self.assertIn("run", rewritten)
        self.assertIn("document", rewritten)
        self.assertNotIn("the", rewritten)

    def test_rewrite_query_drops_hinglish_fillers(self):
        rewritten = _rewrite_query("batao kya hai refund policy ke baare mein")
        self.assertIn("refund", rewritten)
        self.assertIn("polici", rewritten)
        self.assertNotIn("batao", rewritten)
        self.assertNotIn("kya", rewritten)
        self.assertNotIn("hai", rewritten)
        self.assertNotIn("mein", rewritten)

    def test_dedupe_preserves_different_facts_and_sources(self):
        chunks = [
            Document(text="Welcome to our annual report. The company grew a lot this year."),
            Document(text="Welcome to our annual report. The company grew a lot this year!"),
            Document(text="Revenues increased by 12 percent over the fiscal year."),
        ]
        deduped = _dedupe_exact_nodes(chunks + [chunks[0]])
        self.assertEqual(deduped, chunks)


class EcoContextTests(unittest.TestCase):
    def test_context_budget_normal_by_default(self):
        with patch("utils.llama_index.st", SimpleNamespace(session_state={})):
            self.assertEqual(_context_char_budget(), 4800)

    def test_context_budget_shrinks_in_eco_mode(self):
        with patch(
            "utils.llama_index.st", SimpleNamespace(session_state={"eco_mode": True})
        ):
            self.assertEqual(_context_char_budget(), 3200)


class _FakeDocstore:
    def __init__(self, nodes):
        self._nodes = {node.node_id: node for node in nodes}

    def get_node(self, node_id):
        return self._nodes[node_id]


class _FakeVectorRetriever:
    def __init__(self, results):
        self._results = results

    def retrieve(self, query):
        return self._results


class HybridRetrieverCredibilityTests(unittest.TestCase):
    """Weak vector scores must be backed by a BM25 keyword hit."""

    def _retriever(self, vector_scores):
        refund = TextNode(
            text="The refund policy allows full refunds within 30 days of purchase.",
            metadata={"file_name": "refund_policy.txt"},
        )
        boilerplate = TextNode(
            text="Copyright DocMind Labs. All rights reserved.",
            metadata={"file_name": "boilerplate.txt"},
        )
        hr = TextNode(
            text="Employees may take 25 vacation days per year.",
            metadata={"file_name": "hr_policy.txt"},
        )
        finance = TextNode(
            text="Revenues increased by 12 percent over the fiscal year.",
            metadata={"file_name": "finance.txt"},
        )
        nodes = [refund, boilerplate, hr, finance]
        docstore = _FakeDocstore(nodes)
        corpus = [node.node_id for node in nodes]
        vector = _FakeVectorRetriever(
            [
                NodeWithScore(node=refund, score=vector_scores[0]),
                NodeWithScore(node=boilerplate, score=vector_scores[1]),
            ]
        )
        return HybridRetriever(
            vector, docstore, corpus, top_k=3, similarity_cutoff=0.3
        )

    def test_unrelated_query_with_weak_scores_is_rejected(self):
        # 0.46 scores, no keyword overlap with "quantum physics equations".
        retriever = self._retriever([0.46, 0.44])
        self.assertEqual(retriever.retrieve("quantum physics equations"), [])

    def test_keyword_match_keeps_weak_vector_score(self):
        # "refund policy" has an exact BM25 hit even though the vector score
        # is below the evidence floor.
        retriever = self._retriever([0.46, 0.44])
        results = retriever.retrieve("refund policy terms")
        self.assertEqual(len(results), 1)
        self.assertIn("refund", results[0].node.get_content())

    def test_strong_vector_score_needs_no_keyword_evidence(self):
        retriever = self._retriever([0.62, 0.44])
        results = retriever.retrieve("quantum physics equations")
        self.assertEqual(len(results), 1)
        self.assertIn("refund", results[0].node.get_content())


if __name__ == "__main__":
    unittest.main()
