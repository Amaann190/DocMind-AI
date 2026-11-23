import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
for ds in ('scifact','nfcorpus'):
    d=load(f'sweep-{ds}-nomic-embed-text-latest-plain-kw2.json'); q=qrels_for(ds,'test'); T=d['rows']['test']; ids=list(T); n=len(ids)
    a=np.array([ndcg_at_k(T[i]['bm25_only'],q[i],10) for i in ids]); b=np.array([ndcg_at_k(T[i]['bm25_plain'],q[i],10) for i in ids])
    emp=np.array([len(T[i]['bm25_only'])==0 for i in ids]); dif=b-a
    short=np.array([0<len(T[i]['bm25_only'])<10 for i in ids]); full=np.array([len(T[i]['bm25_only'])>=10 for i in ids])
    print(f'{ds}: n={n} DocMind BM25 {a.mean():.4f} plain BM25 {b.mean():.4f} total deficit {dif.mean():.4f} ({dif.sum():.2f} summed)')
    print(f'  empty queries {emp.sum()}: contribution {dif[emp].sum()/n:.4f} ({dif[emp].sum()/dif.sum()*100:.1f}% of deficit); mean plain nDCG on them {b[emp].mean():.3f}')
    print(f'  rest {(~emp).sum()}: contribution {dif[~emp].sum()/n:.4f} ({dif[~emp].sum()/dif.sum()*100:.1f}%); of which non-empty <10 docs {short.sum()}: {dif[short].sum()/n:.4f}; full-10 lists {full.sum()}: {dif[full].sum()/n:.4f}')
    print('  per-query diff: rest mean (within rest) ',round(dif[~emp].mean(),4),'; share of rest queries where plain>docmind',round((dif[~emp]>0).mean(),3),' ; plain<docmind',round((dif[~emp]<0).mean(),3))
    # CI of the empty-part contribution & rest-part
    for lab,m in (('empty',emp),('rest',~emp)):
        part=np.where(m,dif,0.0); P=pb(part); print(f'  {lab} part paired bootstrap: {P["diff"]:.4f} [{P["lo"]:.4f},{P["hi"]:.4f}]')
    P=pb(dif); print(f'  total {P["diff"]:.4f} [{P["lo"]:.4f},{P["hi"]:.4f}]')
    # recomputed on empty: how many of the empties have relevance retrievable by plain (plain nDCG>0)
    print('  empties where plain nDCG>0:',int((b[emp]>0).sum()),'/',int(emp.sum()))
