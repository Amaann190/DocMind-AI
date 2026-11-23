"""Frozen-pipeline ranking on held-out query sets (SciFact train, NFCorpus dev) vs the test split."""
import json
import numpy as np
from pathlib import Path

OUT = Path(r"paper/results")
CONFIGS = ["vector_only", "bm25_only", "hybrid_no_floor", "floor_0.50", "bm25_plain", "dense_plain", "rrf_plain",
           "convex", "rerank"]


def pb(a, b, n=10000, seed=0):
    a, b = np.asarray(a), np.asarray(b)
    d = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n, len(d)))
    m = d[idx].mean(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    p = min(1.0, 2 * min((np.sum(m <= 0) + 1) / (n + 1), (np.sum(m >= 0) + 1) / (n + 1)))
    return d.mean(), lo, hi, p


for split_name, ds in [("scifact-train", "scifact"), ("nfcorpus-dev", "nfcorpus"), ("scifact", "scifact"), ("nfcorpus", "nfcorpus")]:
    for emb in ["nomic-embed-text", "all-minilm"]:
        f = OUT / f"sweep-{split_name}-{emb}-latest-plain-kw2.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        s = d["summary"]
        conf = s["configurations"]
        pq = s["per_query_ndcg"]
        if split_name == "scifact-train" and emb == "nomic-embed-text":
            print("config keys:", list(conf)[:40])
        row = {c: conf[c]["ndcg@10"] if c in conf and "ndcg@10" in conf[c] else None for c in CONFIGS}
        n = len(d["rows"]["test"])
        print(f"\n{split_name:14s} {emb:17s} n={n} cal_floor={s.get('calibrated_floor')}")
        print("  " + "  ".join(f"{c}={v:.3f}" for c, v in row.items() if v is not None))
        h = pq.get("hybrid_no_floor")
        for other in ["rrf_plain", "convex", "rerank", "dense_plain"]:
            if h is not None and other in pq:
                dm, lo, hi, p = pb(h, pq[other])
                print(f"  hybrid - {other:13s} {dm:+.3f} [{lo:+.3f},{hi:+.3f}] p={p:.4f}")
