import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
EF={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest','mxbai':'mxbai-embed-large-latest'}
def fname(pref,e): return f'sweep-{pref}-{EF[e]}-plain.json' if e=='mxbai' else f'sweep-{pref}-{EF[e]}-plain-kw2.json'
def holm(ps):
    o=sorted(range(len(ps)),key=lambda i:ps[i]); adj=[0]*len(ps); run=0
    for r,i in enumerate(o): run=max(run,min(1,(len(ps)-r)*ps[i])); adj[i]=run
    return adj
def nd(rows,q,n): return np.array([ndcg_at_k(rows[i][n],q[i],10) for i in rows])
A=[]
for ds,held,sp in (('scifact','scifact-train','train'),('nfcorpus','nfcorpus-dev','dev')):
    for e in ('nomic','minilm','mxbai'):
        d=load(fname(ds,e)); q=qrels_for(ds,'test'); T=d['rows']['test']
        A.append((f'test {ds}/{e}',len(T),nd(T,q,'hybrid_no_floor'),nd(T,q,'vector_only')))
    for e in ('nomic','minilm'):
        d=load(fname(held,e)); q=qrels_for(ds,sp); T=d['rows']['test']
        A.append((f'held-out {held}/{e}',len(T),nd(T,q,'hybrid_no_floor'),nd(T,q,'vector_only')))
rows=[]
for lab,n,h,v in A:
    P=pb(h-v); rows.append((lab,n,h.mean(),v.mean(),P))
adjA=holm([r[4]['p'] for r in rows])
print('FAMILY A (hybrid_no_floor - vector_only nDCG@10)')
print('| row | n | hybrid | vector | delta | 95% CI | raw p | Holm p |')
for r,a in zip(rows,adjA): print(f"| {r[0]} | {r[1]} | {r[2]:.3f} | {r[3]:.3f} | {r[4]['diff']:+.3f} | [{r[4]['lo']:+.3f},{r[4]['hi']:+.3f}] | {r[4]['p']:.4f} | {a:.4f} |")
B=[]
for ds in ('scifact','nfcorpus'):
    for e in ('nomic','minilm','mxbai'):
        d=load(fname(ds,e)); q=qrels_for(ds,'test'); T=d['rows']['test']; f=d['summary']['calibrated_floor']
        dd=nd(T,q,f'floor_{f:.2f}')-nd(T,q,'hybrid_no_floor'); P=pb(dd); m=boot(dd)
        lo90,hi90=np.percentile(m,[5,95]); p1=((m<=-0.01).sum()+1)/(10001); p2=((m>=0.01).sum()+1)/10001; praw=max((m<=-0.01).mean(),(m>=0.01).mean())
        B.append((f'{ds}/{e}',f,P,lo90,hi90,max(p1,p2),praw))
adjB=holm([b[5] for b in B])
print('FAMILY B (calibrated vs no floor; TOST margin 0.01)')
print('| row | f* | delta | 95% CI | 90% CI | TOST p (+1) | TOST p (raw as reanalysis.py) | Holm TOST p | equivalent @0.05 after Holm |')
for b,a in zip(B,adjB): print(f"| {b[0]} | {b[1]} | {b[2]['diff']:+.3f} | [{b[2]['lo']:+.3f},{b[2]['hi']:+.3f}] | [{b[3]:+.3f},{b[4]:+.3f}] | {b[5]:.4f} | {b[6]:.4f} | {a:.4f} | {a<0.05} |")
