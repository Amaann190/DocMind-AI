import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
EMBF={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest','mxbai':'mxbai-embed-large-latest'}
LAB={'bm25_plain':'plain BM25','dense_plain':'plain dense','rrf_plain':'plain RRF','convex':'convex fusion','rerank':'RRF+cross-enc rerank','bm25_only':'DocMind BM25','vector_only':'DocMind dense (cut 0.3)','hybrid_no_floor':'DocMind hybrid no floor','floor_0.50':'DocMind hybrid f=0.50','kw2_bm25_only':'kw2 BM25','kw2_hybrid_no_floor':'kw2 hybrid no floor','kw2_floor_0.50':'kw2 hybrid f=0.50'}
res={}
for ds in ('scifact','nfcorpus'):
    tq=qrels_for(ds,'test')
    for e,ef in EMBF.items():
        fn=f'sweep-{ds}-{ef}-plain-kw2.json' if e!='mxbai' else f'sweep-{ds}-{ef}-plain.json'
        d=load(fn); rows=d['rows']['test']; off=d['rows']['offtopic']
        names=[n for n in rows[next(iter(rows))] if n!='query']
        pq=per_query(rows,tq,names)
        cal=d['summary'].get('calibrated_floor')
        table={}
        for n in names:
            v=pq[n]; rej=sum(1 for r in off.values() if not r[n])
            table[n]=dict(ndcg=float(v['ndcg'].mean()),hit=float(v['hit'].mean()),rec=float(v['rec'].mean()),empty=float(v['empty'].mean()),docs=float(v['docs'].mean()),fiqa=rej/len(off))
            # check vs stored
        chk=max(abs(table[n]['ndcg']-d['summary']['configurations'][n]['ndcg@10']) for n in names)
        chk2=max(abs(table[n]['rec']-d['summary']['configurations'][n]['true_recall@10']) for n in names)
        plain=['bm25_plain','dense_plain','rrf_plain','convex','rerank']
        best=max(plain,key=lambda n:table[n]['ndcg'])
        P={}
        for ref in plain+['vector_only','bm25_only']:
            P[f'hybrid_no_floor-{ref}']=pb(pq['hybrid_no_floor']['ndcg']-pq[ref]['ndcg'])
        if 'kw2_hybrid_no_floor' in pq:
            P[f'kw2_hybrid_no_floor-{best}']=pb(pq['kw2_hybrid_no_floor']['ndcg']-pq[best]['ndcg'])
        P[f'floor_0.50-{best}']=pb(pq['floor_0.50']['ndcg']-pq[best]['ndcg'])
        P['rrf_plain-hybrid_no_floor(neg)']=pb(pq['rrf_plain']['ndcg']-pq['hybrid_no_floor']['ndcg'])
        P['rerank-hybrid_no_floor']=pb(pq['rerank']['ndcg']-pq['hybrid_no_floor']['ndcg'])
        if cal: 
            P[f'floor_{cal:.2f}-{best}']=pb(pq[f'floor_{cal:.2f}']['ndcg']-pq[best]['ndcg'])
            table['_cal']=cal
        # fusion gain over dense
        P['gain_hyb_vec']=pb(pq['hybrid_no_floor']['ndcg']-pq['vector_only']['ndcg'])
        P['gain_hyb_densePlain']=pb(pq['hybrid_no_floor']['ndcg']-pq['dense_plain']['ndcg'])
        P['gain_rrfPlain_densePlain']=pb(pq['rrf_plain']['ndcg']-pq['dense_plain']['ndcg'])
        res[(ds,e)]=dict(table=table,best=best,paired=P,chk=(chk,chk2),alpha=d['plain']['alpha'],cal=cal,ids=list(rows),pq={k:pq[k]['ndcg'] for k in ('hybrid_no_floor','vector_only','dense_plain','rrf_plain')},n=len(rows),file=fn,nfq=len(off))
# print
for (ds,e),o in res.items():
    print(f'### {ds}/{e} file={o["file"]} n={o["n"]} alpha={o["alpha"]} cal_floor={o["cal"]} chk={o["chk"]} strongest plain={o["best"]}')
    for n,v in o['table'].items():
        if n=='_cal': continue
        print(f'  {n:22s} nDCG {v["ndcg"]:.3f} Hit {v["hit"]:.3f} Rec {v["rec"]:.3f} empty {v["empty"]:.3f} docs {v["docs"]:.2f} fiqaRej {v["fiqa"]:.3f}')
    for k,v in o['paired'].items(): print(f'    {k}: {v["diff"]:+.3f} [{v["lo"]:+.3f},{v["hi"]:+.3f}] p={v["p"]:.4f}')
# mxbai vs nomic gain contrast on same queries
print('=== gain contrasts')
for ds in ('scifact','nfcorpus'):
    for other in ('nomic','minilm'):
        a=res[(ds,'mxbai')]; b=res[(ds,other)]
        assert a['ids']==b['ids']
        for key,(x,y) in {'hyb-vec':('hybrid_no_floor','vector_only'),'hyb-densePlain':('hybrid_no_floor','dense_plain')}.items():
            ga=a['pq'][x]-a['pq'][y]; gb=b['pq'][x]-b['pq'][y]
            print(ds,'mxbai gain minus',other,'gain',key,'mx',round(ga.mean(),3),other,round(gb.mean(),3),{k:round(v,4) for k,v in pb(ga-gb).items()})
import pickle
pickle.dump({k:{kk:vv for kk,vv in v.items() if kk not in('pq',)} for k,v in res.items()},open(r"paper/analysis/taskEF.pkl",'wb'))
