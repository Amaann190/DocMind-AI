"""Checks for review round 3: calibration-side cost, without-replacement calibration draws, truncation vs best baseline."""
import sys
sys.path.insert(0, "paper/analysis")
from common_sw import *  # noqa: F401,F403
from t1 import FL, NAMES, choose, fname

# (a) NFCorpus train-100 -> dev: cost of the selected floor on its own calibration sample.
for e in ("nomic", "minilm"):
    d = load(fname("nfcorpus-dev", e))
    C = d["rows"]["calib"]
    q = qrels_for("nfcorpus", "train")
    pq = per_query(C, q, NAMES)
    H = np.array([pq[n]["hit"] for n in NAMES]).T
    f = choose(H)
    n0, nf = pq["hybrid_no_floor"], pq[f"floor_{f:.2f}"]
    lost = int(((n0["hit"] == 1) & (nf["hit"] == 0)).sum())
    gained = int(((n0["hit"] == 0) & (nf["hit"] == 1)).sum())
    r = pb(nf["ndcg"] - n0["ndcg"])
    print(f"(a) NFC train-100 calib {e}: f*={f} hits {int(n0['hit'].sum())}->{int(nf['hit'].sum())} "
          f"(lost {lost}, gained {gained}) empty {int(n0['empty'].sum())}->{int(nf['empty'].sum())} "
          f"dnDCG {r['diff']:+.4f} [{r['lo']:+.4f},{r['hi']:+.4f}]")
    for tol in (0.95, 0.97, 0.98, 0.99):
        print(f"     tol {tol}: f*={choose(H, tol)}")

# (b) SciFact: draw 100 distinct train queries (of 809) 5,000 times, select f*, apply to fixed test split.
for e in ("nomic", "minilm"):
    hd = load(fname("scifact-train", e))
    TR = hd["rows"]["test"]
    trq = qrels_for("scifact", "train")
    ptr = per_query(TR, trq, NAMES)
    Htr = np.array([ptr[n]["hit"] for n in NAMES]).T
    td = load(fname("scifact", e))
    TE = td["rows"]["test"]
    teq = qrels_for("scifact", "test")
    pte = per_query(TE, teq, NAMES)
    base = pte["hybrid_no_floor"]["ndcg"].mean()
    rng = np.random.default_rng(7)
    losses, picks = [], {}
    for _ in range(5000):
        idx = rng.choice(len(Htr), size=100, replace=False)
        f = choose(Htr[idx])
        picks[f] = picks.get(f, 0) + 1
        name = "hybrid_no_floor" if f is None else f"floor_{f:.2f}"
        losses.append(pte[name]["ndcg"].mean() - base)
    losses = np.array(losses)
    print(f"(b) SciFact {e}: P(loss>0.01)={np.mean(losses < -0.01):.3f} mean {losses.mean():+.4f} "
          f"picks { {k: round(v / 5000, 3) for k, v in sorted(picks.items(), key=lambda x: (x[0] is None, x[0] or 0))} }")

# (c) Hybrid minus best plain baseline, before and after truncating the baseline to the hybrid's per-query depth.
PLAIN = ["bm25_plain", "dense_plain", "rrf_plain", "convex", "rerank"]
for ds in ("scifact", "nfcorpus"):
    q = qrels_for(ds, "test")
    for e in ("nomic", "minilm", "mxbai"):
        d = load(fname(ds, e))
        T = d["rows"]["test"]
        ids = list(T)
        hyb = np.array([ndcg_at_k(T[i]["hybrid_no_floor"], q[i], 10) for i in ids])
        best = max(PLAIN, key=lambda n: np.mean([ndcg_at_k(T[i][n], q[i], 10) for i in ids]))
        full = np.array([ndcg_at_k(T[i][best], q[i], 10) for i in ids])
        trunc = np.array([ndcg_at_k(T[i][best][:len(T[i]["hybrid_no_floor"])], q[i], 10) for i in ids])
        a, b = pb(hyb - full), pb(hyb - trunc)
        print(f"(c) {ds} {e} best={best}: hybrid-best {a['diff']:+.4f} [{a['lo']:+.4f},{a['hi']:+.4f}]; "
              f"hybrid-truncated {b['diff']:+.4f} [{b['lo']:+.4f},{b['hi']:+.4f}]")
