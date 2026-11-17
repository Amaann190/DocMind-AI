"""Public benchmark suite: BEIR SciFact ranking quality for the four retrieval configurations."""
import time
from unittest.mock import patch

from evaluation.benchmark import ranked_files, recall_at_k, reciprocal_rank
from evaluation.common import summarize_results
from evaluation.public import ensure_scifact, load_scifact, ndcg_at_k
from utils import runtime

K = 10


def suite_public(mock: bool, endpoint="http://localhost:11434", model="nomic-embed-text:latest"):
    """Rank 5,183 SciFact abstracts for 300 test claims; report Recall@k, MRR@10 and nDCG@10."""
    print("\n[Suite] Public benchmark (BEIR SciFact)")
    from llama_index.core import Document

    from utils.llama_index import build_hybrid_retriever, create_index

    corpus, queries, qrels = load_scifact(ensure_scifact())
    results = [{"test": "dataset", "pass": len(corpus) == 5183 and len(queries) == 300,
                "detail": f"{len(corpus)} abstracts, {len(queries)} test claims"}]
    documents = [Document(text=text, metadata={"file_name": f"{doc_id}.txt"}) for doc_id, text in corpus.items()]
    started = time.perf_counter()
    index = create_index(documents)
    index_seconds = round(time.perf_counter() - started, 1)
    print(f"  indexed {len(documents)} abstracts in {index_seconds}s")

    class VectorOnly:
        def __init__(self, inner, cutoff=0.3):
            self.inner = inner
            self.cutoff = cutoff

        def retrieve(self, query):
            return [n for n in self.inner.retrieve(query) if n.score >= self.cutoff]

    def hybrid(**options):
        return build_hybrid_retriever(index.as_retriever(similarity_top_k=K), index, top_k=K,
                                      similarity_cutoff=0.3, **options)

    retrievers = {"vector_only": VectorOnly(index.as_retriever(similarity_top_k=K)),
                  "bm25_only": hybrid(use_vector=False), "hybrid_no_floor": hybrid(evidence_floor=None),
                  "full": hybrid()}
    summary = {"embedding": "hash-mock" if mock else model, "corpus": len(corpus), "queries": len(queries),
               "index_seconds": index_seconds, "configurations": {}}
    # Rank up to K documents; the answer-time context budget would truncate hybrid lists.
    # HybridRetriever reads Top K and the cutoff from live session settings on every query;
    # pin them so every configuration returns the same number of results.
    runtime.st.session_state.update(top_k=K, similarity_cutoff=0.3)
    with patch("utils.llama_index.retrieval._context_char_budget", return_value=10**9):
        for name, retriever in retrievers.items():
            recall = {1: [], 5: [], 10: []}
            mrr, ndcg, empty = [], [], 0
            for query_id, text in queries.items():
                ranked = [f.removesuffix(".txt") for f in ranked_files(retriever.retrieve(text))][:K]
                relevant = set(qrels[query_id])
                empty += not ranked
                for k in recall:
                    recall[k].append(recall_at_k(ranked, relevant, k))
                mrr.append(reciprocal_rank(ranked, relevant, K))
                ndcg.append(ndcg_at_k(ranked, qrels[query_id], K))
            stats = {f"recall@{k}": round(sum(v) / len(v), 3) for k, v in recall.items()}
            stats.update({"mrr@10": round(sum(mrr) / len(mrr), 3), "ndcg@10": round(sum(ndcg) / len(ndcg), 3),
                          "no_result": round(empty / len(queries), 3)})
            summary["configurations"][name] = stats
            print(f"  {name:16s} nDCG@10 {stats['ndcg@10']:.3f}  R@10 {stats['recall@10']:.0%}  "
                  f"MRR@10 {stats['mrr@10']:.3f}  no result {stats['no_result']:.0%}")
    results.append({"test": "public_benchmark_executed", "pass": True,
                    "detail": f"{len(queries)} claims x {len(retrievers)} configurations; metrics are in the summary"})
    return summarize_results("public", results, summary=summary)


def markdown_report(summary):
    lines = ["## Public benchmark: BEIR SciFact", "",
             f"{summary['queries']} test claims over {summary['corpus']} abstracts · embeddings: "
             f"{summary['embedding']} · indexing took {summary['index_seconds']} s. "
             "No result = share of claims for which the configuration returned nothing.", "",
             "| Configuration | nDCG@10 | Recall@1 | Recall@5 | Recall@10 | MRR@10 | No result |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, s in summary["configurations"].items():
        lines.append(f"| {name} | {s['ndcg@10']:.3f} | {s['recall@1']:.0%} | {s['recall@5']:.0%} | "
                     f"{s['recall@10']:.0%} | {s['mrr@10']:.3f} | {s['no_result']:.0%} |")
    return lines
