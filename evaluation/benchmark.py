"""Labelled retrieval benchmark: Recall@k, MRR and correct rejection per configuration.

The dataset lives in ``evaluation/benchmark/``: ``corpus.json`` (20 documents) and
``queries.json`` (answerable, off-topic and near-miss queries). Metrics here are
pure functions; ``eval_harness.py --suite benchmark`` builds the index and the
retrievers and calls :func:`evaluate`.

Metrics, per configuration:
- Recall@k: share of answerable queries with a relevant file in the top k
  distinct retrieved files.
- MRR@k: mean reciprocal rank of the first relevant file within the top k.
- Correct rejection: share of off-topic queries for which nothing is retrieved.
- Near-miss retrieval: share of near-miss queries for which something is
  retrieved. Informational only: the related document is a reasonable thing to
  retrieve, and abstention for these must come from the answer step.
"""
import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "benchmark"
K_VALUES = (1, 3, 5)
K_MAX = max(K_VALUES)


def load_dataset(data_dir=DATA_DIR):
    corpus = json.loads((Path(data_dir) / "corpus.json").read_text(encoding="utf-8"))
    queries = json.loads((Path(data_dir) / "queries.json").read_text(encoding="utf-8"))
    return corpus, queries


def ranked_files(nodes):
    """Distinct source files in retrieval order (several chunks can share a file)."""
    files = []
    for node in nodes:
        name = (node.node.metadata or {}).get("file_name", "")
        if name and name not in files:
            files.append(name)
    return files


def recall_at_k(ranked, relevant, k):
    return 1.0 if any(name in relevant for name in ranked[:k]) else 0.0


def reciprocal_rank(ranked, relevant, k):
    for position, name in enumerate(ranked[:k], start=1):
        if name in relevant:
            return 1.0 / position
    return 0.0


def _mean(values):
    return round(sum(values) / len(values), 3) if values else 0.0


def evaluate(retrievers, queries, k_max=K_MAX):
    """Run every query through every retriever; return (summary, rows)."""
    rows = []
    for kind in ("answerable", "off_topic", "near_miss"):
        for item in queries[kind]:
            row = {"id": item["id"], "kind": kind, "query": item["query"],
                   "category": item.get("category", kind), "relevant": item.get("relevant", [])}
            for name, retriever in retrievers.items():
                start = time.perf_counter()
                ranked = ranked_files(retriever.retrieve(item["query"]))[:k_max]
                row[f"{name}_ranked"] = ranked
                row[f"{name}_ms"] = round((time.perf_counter() - start) * 1000, 2)
            rows.append(row)

    answerable = [r for r in rows if r["kind"] == "answerable"]
    off_topic = [r for r in rows if r["kind"] == "off_topic"]
    near_miss = [r for r in rows if r["kind"] == "near_miss"]
    summary = {"answerable": len(answerable), "off_topic": len(off_topic), "near_miss": len(near_miss),
               "configurations": {}, "by_category": {}}
    for name in retrievers:
        stats = {f"recall@{k}": _mean([recall_at_k(r[f"{name}_ranked"], r["relevant"], k) for r in answerable])
                 for k in K_VALUES}
        stats[f"mrr@{k_max}"] = _mean([reciprocal_rank(r[f"{name}_ranked"], r["relevant"], k_max) for r in answerable])
        stats["correct_rejection"] = _mean([1.0 if not r[f"{name}_ranked"] else 0.0 for r in off_topic])
        stats["near_miss_retrieved"] = _mean([1.0 if r[f"{name}_ranked"] else 0.0 for r in near_miss])
        stats["mean_ms"] = round(sum(r[f"{name}_ms"] for r in rows) / len(rows), 2) if rows else 0.0
        summary["configurations"][name] = stats
        for category in sorted({r["category"] for r in answerable}):
            subset = [r for r in answerable if r["category"] == category]
            summary["by_category"].setdefault(category, {"queries": len(subset)})[name] = _mean(
                [recall_at_k(r[f"{name}_ranked"], r["relevant"], k_max) for r in subset])
    return summary, rows


def markdown_report(summary, embedding):
    """Human-readable tables for eval_report.md."""
    k_max = max(K_VALUES)
    lines = ["## Retrieval benchmark", "",
             f"{summary['answerable']} answerable, {summary['off_topic']} off-topic and "
             f"{summary['near_miss']} near-miss queries over 20 documents · embeddings: {embedding}.",
             "Recall@k counts distinct source files. Correct rejection = nothing retrieved for an off-topic query.",
             "Near-miss retrieved is informational: retrieving the related document is acceptable there.", "",
             "| Configuration | Recall@1 | Recall@3 | Recall@5 | MRR@5 | Correct rejection | Near-miss retrieved | ms |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, s in summary["configurations"].items():
        lines.append(f"| {name} | {s['recall@1']:.0%} | {s['recall@3']:.0%} | {s['recall@5']:.0%} | "
                     f"{s[f'mrr@{k_max}']:.3f} | {s['correct_rejection']:.0%} | {s['near_miss_retrieved']:.0%} | "
                     f"{s['mean_ms']} |")
    names = list(summary["configurations"])
    lines.extend(["", f"Recall@{k_max} by query category:", "",
                  "| Category | Queries | " + " | ".join(names) + " |",
                  "|---|---:|" + "---:|" * len(names)])
    for category, values in summary["by_category"].items():
        lines.append(f"| {category} | {values['queries']} | "
                     + " | ".join(f"{values[n]:.0%}" for n in names) + " |")
    return lines
