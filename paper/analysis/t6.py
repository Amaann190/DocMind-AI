import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
EF={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest','mxbai':'mxbai-embed-large-latest'}
for ds in ('scifact','nfcorpus'):
    for e,ef in EF.items():
        fn=f'sweep-{ds}-{ef}-plain-kw2.json' if e!='mxbai' else f'sweep-{ds}-{ef}-plain.json'
        d=load(fn); T=d['rows']['test']; O=d['rows']['offtopic']; n=len(T)
        s=[]
        for c in ('bm25_plain','dense_plain','rrf_plain','convex','rerank','bm25_only','vector_only','hybrid_no_floor'):
            L=[len(set(r[c])) for r in T.values()]
            s.append(f"{c}: docs {np.mean(L):.2f}, <10: {100*np.mean([l<10 for l in L]):.1f}% ({sum(l<10 for l in L)}), empty {sum(l==0 for l in L)}/{n}, FiQA empty {sum(1 for r in O.values() if len(r[c])==0)}/300, min {min(L)}")
        print(f'## {ds}/{e} ({fn}) n={n} alpha={d["plain"]["alpha"]}'); print('\n'.join('  '+x for x in s))
