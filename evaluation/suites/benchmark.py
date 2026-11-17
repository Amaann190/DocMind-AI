"""Labelled retrieval benchmark suite (20 documents)."""
import shutil
import tempfile
from pathlib import Path

from evaluation.common import summarize_results


def suite_benchmark(mock: bool, endpoint="http://localhost:11434", model="nomic-embed-text:latest"):
    """Labelled 20-document benchmark: Recall@k, MRR and rejection for four configurations."""
    print("\n[Suite] Retrieval benchmark (labelled)")
    from unittest.mock import patch

    from evaluation.benchmark import evaluate, load_dataset
    from utils.llama_index import build_hybrid_retriever, create_index, load_documents

    corpus, queries = load_dataset()
    files = {doc["file"] for doc in corpus}
    missing = sorted({f for q in queries["answerable"] for f in q["relevant"]} - files)
    results = [{"test": "dataset_integrity",
                "pass": not missing and len(queries["answerable"]) >= 60 and len(queries["off_topic"]) >= 30,
                "detail": f"{len(corpus)} documents, {len(queries['answerable'])} answerable, "
                          f"{len(queries['off_topic'])} off-topic, {len(queries['near_miss'])} near-miss"
                          + (f"; unknown relevant files: {missing}" if missing else "")}]
    tmpdir = tempfile.mkdtemp(prefix="docmind_benchmark_")
    try:
        for doc in corpus:
            Path(tmpdir, doc["file"]).write_text(doc["text"], encoding="utf-8")
        index = create_index(load_documents(tmpdir))
        k = 5

        class VectorOnly:
            """Dense top-k with the similarity cutoff only."""
            def __init__(self, inner, cutoff=0.3):
                self.inner = inner
                self.cutoff = cutoff

            def retrieve(self, query):
                return [n for n in self.inner.retrieve(query) if n.score >= self.cutoff]

        def hybrid(**options):
            return build_hybrid_retriever(index.as_retriever(similarity_top_k=k), index, top_k=k,
                                          similarity_cutoff=0.3, **options)

        retrievers = {
            "vector_only": VectorOnly(index.as_retriever(similarity_top_k=k)),
            "bm25_only": hybrid(use_vector=False),
            "hybrid_no_floor": hybrid(evidence_floor=None),
            "full": hybrid(),
        }
        for retriever in retrievers.values():
            retriever.retrieve("warm up")
        # Rank up to Top K files. The answer-time context budget would otherwise cut
        # hybrid lists short and make Recall@5 incomparable with the vector baseline.
        with patch("utils.llama_index.retrieval._context_char_budget", return_value=10**9):
            summary, rows = evaluate(retrievers, queries, k_max=k)
        summary["embedding"] = "hash-mock" if mock else model
        for name, stats in summary["configurations"].items():
            print(f"  {name:16s} R@1 {stats['recall@1']:.0%}  R@3 {stats['recall@3']:.0%}  "
                  f"R@5 {stats['recall@5']:.0%}  MRR {stats['mrr@5']:.3f}  "
                  f"reject {stats['correct_rejection']:.0%}  near-miss retrieved {stats['near_miss_retrieved']:.0%}")
        results.append({"test": "benchmark_executed", "pass": True,
                        "detail": f"{len(rows)} queries x {len(retrievers)} configurations; metrics are in the summary"})
        return summarize_results("benchmark", results, summary=summary, rows=rows)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
