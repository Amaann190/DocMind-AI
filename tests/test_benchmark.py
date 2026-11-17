"""Benchmark metrics, dataset integrity and the keyword-evidence rule they measure."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llama_index.core.schema import TextNode

from evaluation.benchmark import evaluate, load_dataset, recall_at_k, reciprocal_rank
from utils import llama_index as rag


class MetricTests(unittest.TestCase):
    def test_recall_at_k(self):
        ranked = ["a.md", "b.md", "c.md"]
        self.assertEqual(recall_at_k(ranked, ["b.md"], 1), 0.0)
        self.assertEqual(recall_at_k(ranked, ["b.md"], 2), 1.0)
        self.assertEqual(recall_at_k([], ["b.md"], 5), 0.0)

    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank(["a.md", "b.md"], ["b.md"], 5), 0.5)
        self.assertEqual(reciprocal_rank(["a.md", "b.md"], ["c.md"], 5), 0.0)
        self.assertEqual(reciprocal_rank(["a.md", "b.md", "c.md"], ["c.md"], 2), 0.0)

    def test_evaluate_counts_rejection_and_distinct_files(self):
        def node(name):
            return SimpleNamespace(node=SimpleNamespace(metadata={"file_name": name}))

        class Fixed:
            def retrieve(self, query):
                return [node("x.md"), node("x.md"), node("y.md")] if "known" in query else []

        queries = {"answerable": [{"id": "a", "query": "known fact", "category": "keyword", "relevant": ["y.md"]}],
                   "off_topic": [{"id": "o", "query": "unrelated"}],
                   "near_miss": [{"id": "n", "query": "known-ish"}]}
        summary, rows = evaluate({"fixed": Fixed()}, queries)
        stats = summary["configurations"]["fixed"]
        self.assertEqual(rows[0]["fixed_ranked"], ["x.md", "y.md"])
        self.assertEqual((stats["recall@1"], stats["recall@3"], stats["mrr@5"]), (0.0, 1.0, 0.5))
        self.assertEqual(stats["correct_rejection"], 1.0)
        self.assertEqual(stats["near_miss_retrieved"], 1.0)


class DatasetTests(unittest.TestCase):
    def test_dataset_is_large_enough_and_consistent(self):
        corpus, queries = load_dataset()
        files = {doc["file"] for doc in corpus}
        self.assertEqual(len(files), len(corpus))
        self.assertGreaterEqual(len(corpus), 20)
        self.assertGreaterEqual(len(queries["answerable"]), 60)
        self.assertGreaterEqual(len(queries["off_topic"]), 30)
        ids = [q["id"] for kind in ("answerable", "off_topic", "near_miss") for q in queries[kind]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in queries["answerable"]:
            self.assertTrue(set(item["relevant"]) <= files, item["id"])
        for item in queries["near_miss"]:
            self.assertTrue(set(item["related"]) <= files, item["id"])


class KeywordEvidenceTests(unittest.TestCase):
    def retriever(self, *texts):
        nodes = [TextNode(text=text) for text in texts]
        store = Mock()
        store.get_node.side_effect = {n.node_id: n for n in nodes}.get
        vector = Mock()
        vector.retrieve.return_value = []
        return rag.HybridRetriever(vector, store, [n.node_id for n in nodes], 3), nodes

    def retrieve(self, retriever, query):
        with patch("utils.runtime.st", SimpleNamespace(session_state={})):
            return [n.node.get_content() for n in retriever.retrieve(query)]

    def test_function_words_are_not_evidence(self):
        retriever, _ = self.retriever("How to reset the router: hold the button for 10 seconds.")
        self.assertEqual(self.retrieve(retriever, "How tall is Mount Kilimanjaro?"), [])

    def test_one_incidental_word_is_not_evidence(self):
        retriever, _ = self.retriever("Boil the spaghetti for 10 minutes in salted water.")
        self.assertEqual(self.retrieve(retriever, "What is the boiling point of nitrogen?"), [])

    def test_enough_content_terms_are_evidence(self):
        retriever, _ = self.retriever("Boil the spaghetti for 10 minutes in salted water.")
        self.assertTrue(self.retrieve(retriever, "How long should spaghetti boil?"))

    def test_each_followup_question_is_judged_on_its_own(self):
        retriever, _ = self.retriever("Stream aggregators include Orbit Cinema.")
        query = "Which stream aggregators are listed?\nCan you share a website link for an example?\nnames"
        self.assertTrue(self.retrieve(retriever, query))


if __name__ == "__main__":
    unittest.main()
