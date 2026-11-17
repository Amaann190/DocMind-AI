"""SciFact loader, download verification and nDCG, without network access."""
import io
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from evaluation import public


def write_scifact(folder):
    (folder / "qrels").mkdir(parents=True)
    (folder / "corpus.jsonl").write_text(
        json.dumps({"_id": "d1", "title": "Aspirin", "text": "Aspirin lowers fever."}) + "\n"
        + json.dumps({"_id": "d2", "title": "", "text": "Unrelated abstract."}) + "\n", encoding="utf-8")
    (folder / "queries.jsonl").write_text(
        json.dumps({"_id": "q1", "text": "Aspirin reduces fever."}) + "\n"
        + json.dumps({"_id": "q9", "text": "Training-only claim."}) + "\n", encoding="utf-8")
    (folder / "qrels" / "test.tsv").write_text("query-id\tcorpus-id\tscore\nq1\td1\t1\n", encoding="utf-8")


class NdcgTests(unittest.TestCase):
    def test_perfect_and_missing_rankings(self):
        self.assertEqual(public.ndcg_at_k(["d1", "d2"], {"d1": 1}, 10), 1.0)
        self.assertEqual(public.ndcg_at_k(["d2", "d3"], {"d1": 1}, 10), 0.0)

    def test_relevant_document_at_rank_two(self):
        self.assertAlmostEqual(public.ndcg_at_k(["d2", "d1"], {"d1": 1}, 10), 1 / math.log2(3))

    def test_only_top_k_counts(self):
        self.assertEqual(public.ndcg_at_k(["d2", "d3", "d1"], {"d1": 1}, 2), 0.0)


class LoaderTests(unittest.TestCase):
    def test_loads_test_split_only(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "scifact"
            write_scifact(folder)
            corpus, queries, qrels = public.load_scifact(folder)
        self.assertEqual(corpus["d1"], "Aspirin\n\nAspirin lowers fever.")
        self.assertEqual(corpus["d2"], "Unrelated abstract.")
        self.assertEqual(list(queries), ["q1"])
        self.assertEqual(qrels, {"q1": {"d1": 1}})


class DownloadTests(unittest.TestCase):
    def archive_bytes(self, member="scifact/corpus.jsonl"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            bundle.writestr(member, "{}")
        return buffer.getvalue()

    def test_tampered_download_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_download(url, path):
                Path(path).write_bytes(self.archive_bytes())
            with patch.object(public.urllib.request, "urlretrieve", side_effect=fake_download), \
                    self.assertRaisesRegex(ValueError, "failed verification"):
                public.ensure_scifact(directory)
            self.assertFalse((Path(directory) / "scifact.zip").exists())

    def test_archive_paths_cannot_escape_the_data_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.archive_bytes("../escaped.txt")
            (Path(directory) / "scifact.zip").write_bytes(data)
            digest = __import__("hashlib").sha256(data).hexdigest()
            with patch.object(public, "SCIFACT_SHA256", digest), self.assertRaisesRegex(ValueError, "Unsafe path"):
                public.ensure_scifact(directory)
            self.assertFalse((Path(directory).parent / "escaped.txt").exists())


class SuiteTests(unittest.TestCase):
    def test_suite_ranks_a_tiny_corpus_with_every_configuration(self):
        from evaluation.common import _setup_hash_embeddings, _setup_runtime_state
        from evaluation.suites import public as suite
        from utils.runtime import request_state
        from utils.session_workspace import clear_session_workspace

        corpus = {f"d{i}": f"Topic {i}\n\nAbstract number {i} about subject {i}." for i in range(12)}
        corpus["d3"] = "Aspirin\n\nAspirin lowers fever in adults."
        queries = {"q1": "Aspirin lowers fever."}
        qrels = {"q1": {"d3": 1}}
        state = {}
        with request_state(state), patch.object(suite, "ensure_scifact", return_value=Path(".")), \
                patch.object(suite, "load_scifact", return_value=(corpus, queries, qrels)):
            _setup_runtime_state()
            _setup_hash_embeddings()
            try:
                result = suite.suite_public(mock=True)
            finally:
                clear_session_workspace(state)
        summary = result["summary"]
        self.assertEqual(set(summary["configurations"]), {"vector_only", "bm25_only", "hybrid_no_floor", "full"})
        self.assertEqual(summary["configurations"]["bm25_only"]["recall@1"], 1.0)
        self.assertFalse(result["results"][0]["pass"], "the real dataset has 5,183 abstracts, not 13")
        self.assertIn("nDCG@10", "\n".join(suite.markdown_report(summary)))


if __name__ == "__main__":
    unittest.main()
