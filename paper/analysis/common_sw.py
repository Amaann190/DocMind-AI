import json,sys,numpy as np
from pathlib import Path
sys.path.insert(0,'.')
from evaluation import beir, stats
from evaluation.public import ndcg_at_k
from evaluation import retrieval_ext
R=Path('paper/results')
FOLDER={}
def qrels_for(ds,split):
    f=beir.ensure_beir(ds); return beir.load_split(f,split)[1]
def load(name): return json.load(open(R/name,encoding='utf8'))
def boot(d,B=10000,seed=0):
    d=np.asarray(d,float); n=len(d); rng=np.random.default_rng(seed); idx=rng.integers(0,n,size=(B,n)); return d[idx].mean(1)
def pb(d):
    m=boot(d); d=np.asarray(d); lo,hi=np.percentile(m,[2.5,97.5]); p=min(1.0,2*(min((m<=0).sum(),(m>=0).sum())+1)/(10000+1))
    return dict(diff=float(d.mean()),lo=float(lo),hi=float(hi),p=float(p))
def wil(k,n):
    lo,hi=stats.wilson(k,n); return f'{k/n:.3f} [{lo:.3f},{hi:.3f}] ({k}/{n})'
def per_query(rows,qrels,names,k=10):
    out={}
    for n in names:
        ids=list(rows)
        out[n]=dict(ndcg=np.array([ndcg_at_k(rows[q][n],qrels[q],k) for q in ids]),
                    hit=np.array([retrieval_ext.hit_at_k(rows[q][n],set(qrels[q]),k) for q in ids]),
                    rec=np.array([retrieval_ext.true_recall_at_k(rows[q][n],set(qrels[q]),k) for q in ids]),
                    empty=np.array([float(len(rows[q][n])==0) for q in ids]),
                    docs=np.array([len(set(rows[q][n])) for q in ids],float))
    return out
