import json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, '.')
from evaluation import beir, stats
from evaluation.public import ndcg_at_k
R = Path('output/research'); OUT = Path(sys.argv[1])
EMB = {'nomic': 'nomic-embed-text-latest', 'minilm': 'all-minilm-latest'}
CORP = ['scifact', 'nfcorpus', 'labelled']
B = 10000


def boot(d, iters=B, seed=0):
    d = np.asarray(d, float); n = len(d); rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(iters, n))
    return d[idx].mean(1)


def pb(d, seed=0):
    m = boot(d, seed=seed); d = np.asarray(d)
    lo, hi = np.percentile(m, [2.5, 97.5])
    p = min(1.0, 2 * (min((m <= 0).sum(), (m >= 0).sum()) + 1) / (B + 1))
    return dict(diff=float(d.mean()), lo=float(lo), hi=float(hi), p=float(p))


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0] * len(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def wil(k, n):
    lo, hi = stats.wilson(k, n); return dict(k=k, n=n, rate=k / n, lo=lo, hi=hi)


qj = json.load(open('evaluation/benchmark/queries.json'))
lab_q = {q['id']: {n: 1 for n in q['relevant']} for q in qj['answerable']}
res = {}; holm_in = []
for c in CORP:
    for e, f in EMB.items():
        d = json.load(open(R / f'sweep-{c}-{f}.json')); k = d['k']; rows = d['rows']
        if c == 'labelled':
            qrels = lab_q; cq = {}
        else:
            folder = beir.ensure_beir(c); _, qrels = beir.load_split(folder, 'test')
            _, cq = beir.load_split(folder, 'train' if c == 'scifact' else 'dev')
        T = rows['test']; ids = list(T)
        nd = {n: np.array([ndcg_at_k(T[q][n], qrels[q], k) for q in ids]) for n in d['summary']['per_query_ndcg']}
        chk = max(abs(nd[n].mean() - np.mean(d['summary']['per_query_ndcg'][n])) for n in nd)
        cal = d['summary'].get('calibrated_floor'); cn = f'floor_{cal:.2f}' if cal is not None else None
        o = dict(k=k, n_test=len(ids), calibrated_floor=cal, ndcg_recompute_maxerr=float(chk))
        P = {}
        P['hybrid_vs_vector'] = pb(nd['hybrid_no_floor'] - nd['vector_only'])
        P['hybrid_vs_bm25'] = pb(nd['hybrid_no_floor'] - nd['bm25_only'])
        P['default0.5_vs_nofloor'] = pb(nd['floor_0.50'] - nd['hybrid_no_floor'])
        if cn:
            dd = nd[cn] - nd['hybrid_no_floor']; P['calibrated_vs_nofloor'] = pb(dd)
            m = boot(dd, seed=0); lo90, hi90 = np.percentile(m, [5, 95])
            p1 = (m <= -0.01).mean(); p2 = (m >= 0.01).mean()
            P['tost'] = dict(margin=0.01, ci90=[float(lo90), float(hi90)], p=float(max(p1, p2)),
                             equivalent=bool(lo90 > -0.01 and hi90 < 0.01))
            P['calibrated_vs_default0.5'] = pb(nd[cn] - nd['floor_0.50'])
        o['paired'] = P
        for t in ('hybrid_vs_vector', 'hybrid_vs_bm25'):
            holm_in.append((c, e, t, P[t]['p']))
        o['gain_hyb_vec'] = nd['hybrid_no_floor'] - nd['vector_only']
        O = rows['offtopic']
        if c == 'labelled':
            O = {q: r for q, r in O.items() if q.startswith('fiqa_')}
        conf = {}
        for n in nd:
            lens = [len(T[q][n]) for q in ids]
            hit = [float(any(x in qrels[q] for x in T[q][n][:k])) for q in ids]
            rec = [sum(x in qrels[q] for x in set(T[q][n][:k])) / len(qrels[q]) for q in ids]
            conf[n] = dict(ndcg=float(nd[n].mean()), hit=float(np.mean(hit)), true_recall=float(np.mean(rec)),
                           mean_docs=float(np.mean(lens)), pct_lt_k=float(np.mean([l < k for l in lens])),
                           empty=wil(sum(l == 0 for l in lens), len(ids)),
                           fiqa_reject=wil(sum(not r[n] for r in O.values()), len(O)))
        o['configs'] = conf
        fa = {}
        for lab, n in (('no_floor', 'hybrid_no_floor'), ('default0.5', 'floor_0.50'), ('calibrated', cn)):
            if n:
                fa[lab] = conf[n]['fiqa_reject']
        for lab, n in (('default', 'floor_0.50'), ('calibrated', cn)):
            if n:
                w = sum(1 for r in O.values() if r[n] == [] and r['hybrid_no_floor'] != [])
                l = sum(1 for r in O.values() if r[n] != [] and r['hybrid_no_floor'] == [])
                fa[f'{lab}_minus_nofloor'] = dict(gained=w, lost=l, mcnemar_p=stats.mcnemar_exact(w, l))
        o['floor_attribution'] = fa
        if c != 'labelled':
            C = rows['calib']; cids = list(C); floors = [float(x) for x in d['floors']]

            def mats(kind):
                M = {}
                for n in ['hybrid_no_floor'] + [f'floor_{x:.2f}' for x in floors]:
                    if kind == 'hit':
                        M[n] = np.array([float(any(x in cq[q] for x in C[q][n][:k])) for q in cids])
                    else:
                        M[n] = np.array([sum(x in cq[q] for x in set(C[q][n][:k])) / len(cq[q]) for q in cids])
                return M

            def choose(M, idx, tol):
                ref = M['hybrid_no_floor'][idx].mean()
                q = [x for x in floors if M[f'floor_{x:.2f}'][idx].mean() >= tol * ref]
                return max(q) if q else None
            full = np.arange(len(cids)); cal_out = {}
            for kind in ('hit', 'recall'):
                M = mats(kind)
                cal_out[f'{kind}_full'] = {str(t): choose(M, full, t) for t in (0.95, 0.97, 0.98, 0.99)}
                cal_out[f'{kind}_curve'] = {n: float(v.mean()) for n, v in M.items()}
                rng = np.random.default_rng(0); cnt = {}
                for _ in range(5000):
                    ch = choose(M, rng.integers(0, len(cids), len(cids)), 0.98)
                    cnt[str(ch)] = cnt.get(str(ch), 0) + 1
                cal_out[f'{kind}_boot5000_tol0.98'] = dict(sorted(cnt.items()))
            o['calibration'] = cal_out
        res[(c, e)] = o

beir_only = [h for h in holm_in if h[0] != 'labelled']
a1 = holm([h[3] for h in beir_only]); a2 = holm([h[3] for h in holm_in])
holmres = []
for i, h in enumerate(holm_in):
    holmres.append(dict(corpus=h[0], emb=h[1], test=h[2], p=h[3],
                        holm_beir8=(a1[beir_only.index(h)] if h in beir_only else None), holm_all12=a2[i]))
gains = {}
for c in CORP:
    g = res[(c, 'minilm')]['gain_hyb_vec'] - res[(c, 'nomic')]['gain_hyb_vec']
    gains[c] = dict(gain_nomic=float(res[(c, 'nomic')]['gain_hyb_vec'].mean()),
                    gain_minilm=float(res[(c, 'minilm')]['gain_hyb_vec'].mean()), **pb(g))
for v in res.values():
    v.pop('gain_hyb_vec')
out = dict(by={f'{c}|{e}': v for (c, e), v in res.items()}, holm=holmres, fusion_gain_contrast=gains)
json.dump(out, open(OUT / 'reanalysis.json', 'w'), indent=1, default=float)

L = ['# Re-analysis (bootstrap 10,000 resamples, seed 0, numpy; p = two-sided percentile with +1 correction)', '',
     'Labelled: research.py sets k=5 for the labelled benchmark and scores ndcg_at_k(..., k=5); the JSON key "ndcg@10" is a mislabel, the value is nDCG@5 (Hit@5, depth cap 5). Labelled has no calibration set, so no calibrated floor.', '',
     '## 1 Paired nDCG differences (a - b), 95% CI', '', '|corpus|emb|contrast|diff|lo|hi|p|', '|-|-|-|-:|-:|-:|-:|']
for (c, e), o in res.items():
    for t, v in o['paired'].items():
        if t == 'tost':
            continue
        L.append(f"|{c}|{e}|{t}|{v['diff']:.3f}|{v['lo']:.3f}|{v['hi']:.3f}|{v['p']:.4f}|")
L += ['', '### TOST calibrated vs no floor, margin 0.01 (equivalent if 90% CI within +-0.01)', '|corpus|emb|floor|90% CI|TOST p|equivalent|', '|-|-|-|-|-:|-|']
for (c, e), o in res.items():
    if 'tost' in o['paired']:
        t = o['paired']['tost']
        L.append(f"|{c}|{e}|{o['calibrated_floor']}|[{t['ci90'][0]:.3f},{t['ci90'][1]:.3f}]|{t['p']:.4f}|{t['equivalent']}|")
L += ['', '## 2 Holm (hybrid vs vector / vs BM25)', '|corpus|emb|test|raw p|Holm (8 BEIR tests)|Holm (all 12)|', '|-|-|-|-:|-:|-:|']
for h in holmres:
    hb = '' if h['holm_beir8'] is None else format(h['holm_beir8'], '.4f')
    L.append(f"|{h['corpus']}|{h['emb']}|{h['test']}|{h['p']:.4f}|{hb}|{h['holm_all12']:.4f}|")
L += ['', '## 3 Fusion-gain contrast (minilm gain - nomic gain, hybrid minus vector nDCG)', '|corpus|gain nomic|gain minilm|diff|lo|hi|p|', '|-|-:|-:|-:|-:|-:|-:|']
for c, g in gains.items():
    L.append(f"|{c}|{g['gain_nomic']:.3f}|{g['gain_minilm']:.3f}|{g['diff']:.3f}|{g['lo']:.3f}|{g['hi']:.3f}|{g['p']:.4f}|")
L += ['', '## 4 Calibration stability (hit = Hit@10, recall = true Recall@10; None = no floor qualifies)']
for (c, e), o in res.items():
    if 'calibration' in o:
        cb = o['calibration']
        L += [f"- {c}/{e} (file floor {o['calibrated_floor']}): full-set by tolerance, Hit {cb['hit_full']}; Recall {cb['recall_full']}",
              f"  - bootstrap 5000 at 98%, Hit: {cb['hit_boot5000_tol0.98']}", f"  - bootstrap 5000 at 98%, Recall: {cb['recall_boot5000_tol0.98']}"]
L += ['', '## 5 FiQA off-topic rejection (Wilson 95%)', '|corpus|emb|no floor|default 0.50|calibrated|default adds (gained/lost, McNemar p)|calibrated adds|', '|-|-|-|-|-|-|-|']
f = lambda w: f"{w['rate']:.3f} [{w['lo']:.3f},{w['hi']:.3f}] ({w['k']}/{w['n']})" if w else 'n/a'
g2 = lambda a: f"{a['gained']}/{a['lost']}, p={a['mcnemar_p']:.4f}" if a else 'n/a'
for (c, e), o in res.items():
    a = o['floor_attribution']
    L.append(f"|{c}|{e}|{f(a['no_floor'])}|{f(a['default0.5'])}|{f(a.get('calibrated'))}|{g2(a['default_minus_nofloor'])}|{g2(a.get('calibrated_minus_nofloor'))}|")
L += ['', '## 6/7 Per configuration on test queries: depth, false rejects (empty list), Hit@k vs true Recall@k']
for (c, e), o in res.items():
    L += ['', f"### {c}/{e} (k={o['k']}, n={o['n_test']})", '|config|nDCG|Hit@k|Recall@k|mean docs|% <k docs|empty (false reject)|FiQA reject|', '|-|-:|-:|-:|-:|-:|-|-|']
    for n, v in o['configs'].items():
        L.append(f"|{n}|{v['ndcg']:.3f}|{v['hit']:.3f}|{v['true_recall']:.3f}|{v['mean_docs']:.2f}|{v['pct_lt_k']*100:.1f}%|{f(v['empty'])}|{f(v['fiqa_reject'])}|")
Path(OUT / 'reanalysis.md').write_text('\n'.join(L), encoding='utf-8')
