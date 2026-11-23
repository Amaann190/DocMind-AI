import sys,re; sys.path.insert(0,r"paper/analysis")
from common_sw import *
folder=beir.ensure_beir('scifact')
trq,trr=beir.load_split(folder,'train'); teq,ter=beir.load_split(folder,'test')
norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
nt={q:norm(t) for q,t in trq.items()}; ne={q:norm(t) for q,t in teq.items()}
shared=set(nt.values())&set(ne.values())
dup_tr=[q for q,v in nt.items() if v in shared]; dup_te=[q for q,v in ne.items() if v in shared]
print('train',len(trq),'test',len(teq),'distinct normalized train',len(set(nt.values())),'test',len(set(ne.values())))
print('shared normalized texts',len(shared),'train queries affected',len(dup_tr),'test queries affected',len(dup_te))
# also exact (raw) shared and id overlap
print('raw exact shared',len(set(trq.values())&set(teq.values())),'id overlap',len(set(trq)&set(teq)))
# near duplicates: word-level jaccard >=0.9 
def toks(s): return set(re.findall(r'[a-z0-9]+',s.lower()))
near=0; ex=[]
for q,t in trq.items():
    a=toks(t)
    for q2,t2 in teq.items():
        b=toks(t2)
        if a and len(a&b)/len(a|b)>=0.9 and nt[q]!=ne[q2]: near+=1; ex.append((t,t2))
print('near-duplicates (jaccard>=0.9, not exact-normalized)',near, ex[:3])
for t in list(shared)[:0]: pass
ex=[(trq[q][:90]) for q in dup_tr][:4]; print('examples',ex)
# same relevant docs?
same_rel=0
bytxt={ne[q]:q for q in dup_te}
for q in dup_tr:
    q2=bytxt[nt[q]]; same_rel+= set(trr[q])==set(ter[q2])
print('duplicate pairs with identical qrel doc sets',same_rel,'/',len(dup_tr))
EF={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest'}
for e,ef in EF.items():
    d=load(f'sweep-scifact-train-{ef}-plain-kw2.json'); T=d['rows']['test']
    ids=list(T); keep=[q for q in ids if q not in set(dup_tr)]
    for n in ('hybrid_no_floor','vector_only','dense_plain','floor_0.50'):
        a=np.array([ndcg_at_k(T[q][n],trr[q],10) for q in ids]); k=np.array([q in set(dup_tr) is False for q in ids])
        mask=np.array([q not in set(dup_tr) for q in ids])
        print(e,n,f'all {len(ids)}: {a.mean():.4f} | excl dup {mask.sum()}: {a[mask].mean():.4f} | dup-only {(~mask).sum()}: {a[~mask].mean() if (~mask).sum() else float("nan"):.4f}')
    h=np.array([ndcg_at_k(T[q]['hybrid_no_floor'],trr[q],10) for q in ids]); v=np.array([ndcg_at_k(T[q]['vector_only'],trr[q],10) for q in ids]); mask=np.array([q not in set(dup_tr) for q in ids])
    print(e,'hybrid-dense all',pb(h-v),'excl dup',pb((h-v)[mask]))
