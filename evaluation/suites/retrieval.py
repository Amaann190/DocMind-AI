"""Retrieval suite: four-way ablation on the fixture corpus."""
import shutil
import tempfile

from evaluation.common import (
    _create_index_from_docs,
    _evaluate_retriever,
    _setup_hash_embeddings,
    _setup_runtime_state,
    _try_real_embeddings,
    summarize_results,
)
from evaluation.fixtures import QUERIES


def suite_retrieval(mock: bool, endpoint="http://localhost:11434", model="nomic-embed-text:latest"):
    print("\n[Suite] Retrieval (plain vs hybrid)")
    _setup_runtime_state()
    if mock:
        _setup_hash_embeddings()
    else:
        _try_real_embeddings(endpoint, model)

    tmpdir = tempfile.mkdtemp(prefix="docmind_eval_")
    try:
        from utils.llama_index import HybridRetriever, build_hybrid_retriever
        index = _create_index_from_docs(tmpdir)

        class PlainWrapper:
            """Vector-only baseline: dense top-k with the similarity cutoff only."""
            def __init__(self, inner, cutoff=0.3):
                self.inner = inner
                self.cutoff = cutoff
            def retrieve(self, query):
                nodes = self.inner.retrieve(query)
                return [n for n in nodes if n.score >= self.cutoff]

        # Each configuration gets its own vector retriever: HybridRetriever widens
        # its dense candidate pool, which must not leak into the vector-only baseline.
        retrievers = {
            "vector_only": PlainWrapper(index.as_retriever(similarity_top_k=3), cutoff=0.3),
            "bm25_only": build_hybrid_retriever(index.as_retriever(similarity_top_k=3), index, top_k=3,
                                                similarity_cutoff=0.3, use_vector=False),
            "hybrid_no_floor": build_hybrid_retriever(index.as_retriever(similarity_top_k=3), index, top_k=3,
                                                      similarity_cutoff=0.3, evidence_floor=None),
            "full": build_hybrid_retriever(index.as_retriever(similarity_top_k=3), index, top_k=3,
                                           similarity_cutoff=0.3),
        }
        is_hybrid = isinstance(retrievers["full"], HybridRetriever)
        # Warm every retriever once so the first timed query does not carry
        # model-load or cache-fill cost (that skewed earlier latency numbers).
        for retriever in retrievers.values():
            retriever.retrieve("warm up")

        results = []
        for item in QUERIES:
            q = item["query"]
            exp = item["expected"]
            row = {"query": q, "expected": exp, "feature": item["feature"]}
            # Rotate which configuration runs first: the first dense call for a
            # query pays the embedding cost and later ones can hit caches.
            names = list(retrievers)
            shift = len(results) % len(names)
            for name in names[shift:] + names[:shift]:
                retriever = retrievers[name]
                outcome = _evaluate_retriever(retriever, q, exp)
                row[f"{name}_hit"] = outcome["hit"]
                row[f"{name}_top"] = outcome["top_file"]
                row[f"{name}_score"] = outcome["top_score"]
                row[f"{name}_latency"] = round(outcome["latency"], 4)
            marks = " ".join(f"{name}:{'PASS' if row[name + '_hit'] else 'FAIL'}" for name in retrievers)
            print(f"  {'PASS' if row['full_hit'] else 'FAIL'}  [{item['feature']:12s}] {q[:42]:42s}  {marks}")
            results.append(row)

        factual = [r for r in results if r["feature"] != "no-match"]
        no_match = [r for r in results if r["feature"] == "no-match"]
        def rate(rows, key): return sum(1 for r in rows if r[key]) / len(rows) if rows else 0
        summary = {"answerable_queries": len(factual), "no_match_queries": len(no_match),
                   "is_hybrid": is_hybrid, "embedding": "hash-mock" if mock else model}
        for name in retrievers:
            summary[f"{name}_hit_rate"] = round(rate(factual, f"{name}_hit"), 3)
            summary[f"{name}_rejection"] = round(rate(no_match, f"{name}_hit"), 3)
            summary[f"{name}_avg_ms"] = round(sum(r[f"{name}_latency"] for r in results) / len(results) * 1000, 1)
        # Backward-compatible keys used by earlier reports.
        summary.update(plain_hit_rate=summary["vector_only_hit_rate"], hybrid_hit_rate=summary["full_hit_rate"],
                       plain_rejection=summary["vector_only_rejection"], hybrid_rejection=summary["full_rejection"],
                       plain_avg_ms=summary["vector_only_avg_ms"], hybrid_avg_ms=summary["full_avg_ms"])
        for feat in sorted({r["feature"] for r in results}):
            rows = [r for r in results if r["feature"] == feat]
            summary[f"hybrid_{feat}_rate"] = round(rate(rows, "full_hit"), 3)

        for name in retrievers:
            print(f"  {name:16s} hit {summary[name + '_hit_rate']:.0%} ({len(factual)}) | "
                  f"reject {summary[name + '_rejection']:.0%} ({len(no_match)}) | {summary[name + '_avg_ms']} ms")
        return summarize_results("retrieval", [{**r, "pass": bool(r["full_hit"]), "status": "passed" if r["full_hit"] else "failed"} for r in results], summary=summary)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
