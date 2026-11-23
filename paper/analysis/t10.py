import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
FL=[0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7]; NAMES=['hybrid_no_floor']+[f'floor_{f:.2f}' for f in FL]
def choose(H,tol=0.98):
    m=H.mean(0); q=[f for f,v in zip(FL,m[1:]) if v>=tol*m[0]]; return max(q) if q else None
for ds,cs in (('scifact','train'),('nfcorpus','dev')):
    tq=qrels_for(ds,'test'); cq=qrels_for(ds,cs)
    res={}
    for tag,fn in (('raw',f'sweep-{ds}-nomic-embed-text-latest.json'),('prefix',f'sweep-{ds}-nomic-embed-text-latest-prefix.json')):
        d=load(fn); T=d['rows']['test']; C=d['rows']['calib']; O=d['rows']['offtopic']; ids=list(T)
        nd={n:np.array([ndcg_at_k(T[i][n],tq[i],10) for i in ids]) for n in ['vector_only','bm25_only']+NAMES}
        hit={n:np.array([retrieval_ext.hit_at_k(T[i][n],set(tq[i]),10) for i in ids]) for n in NAMES}
        emp={n:np.array([len(T[i][n])==0 for i in ids]) for n in NAMES}
        H=np.array([[retrieval_ext.hit_at_k(C[i][n],set(cq[i]),10) for n in NAMES] for i in C])
        f=choose(H); fq=lambda n:sum(1 for r in O.values() if not r[n])
        res[tag]=dict(nd=nd,f=f,file_f=d['summary'].get('calibrated_floor'),H=H,fq=fq,emp=emp,hit=hit,docs=np.mean([len(set(T[i]['hybrid_no_floor'])) for i in ids]),n=len(ids),
                      vecfq=fq('vector_only'),bm25fq=fq('bm25_only'),vemp=sum(len(T[i]['vector_only'])==0 for i in ids))
        r=res[tag]
        print(f"## {ds} {tag} ({fn}) n={len(ids)} file f*={r['file_f']} recomputed f*={f}")
        print('  nDCG@10: hybrid_no_floor %.3f | vector_only %.3f | bm25_only %.3f'%tuple(nd[x].mean() for x in ('hybrid_no_floor','vector_only','bm25_only')))
        P=pb(nd['hybrid_no_floor']-nd['vector_only']); print('  hybrid-dense %+.3f [%+.3f,%+.3f] p=%.4f'%(P['diff'],P['lo'],P['hi'],P['p']))
        P=pb(nd['hybrid_no_floor']-nd['bm25_only']); print('  hybrid-bm25  %+.3f [%+.3f,%+.3f] p=%.4f'%(P['diff'],P['lo'],P['hi'],P['p']))
        print('  FiQA rejection (empty list)/300: no floor',fq('hybrid_no_floor'),'| vector_only',fq('vector_only'),'| bm25_only',fq('bm25_only'),'| f=0.50',fq('floor_0.50'),'| f*',fq(f'floor_{f:.2f}') if f else None)
        print('  FiQA rejection by floor:',{x:fq(f'floor_{x:.2f}') for x in FL})
        print('  calib Hit@10 curve (no floor, .35..0.70):',[round(float(v),2) for v in H.mean(0)])
        print('  test nDCG by floor:',[round(float(nd[f'floor_{x:.2f}'].mean()),3) for x in FL])
        if f:
            n=f'floor_{f:.2f}'; P=pb(nd[n]-nd['hybrid_no_floor'])
            print(f"  at f*={f}: nDCG {nd['hybrid_no_floor'].mean():.3f} -> {nd[n].mean():.3f} d={P['diff']:+.4f} [{P['lo']:+.4f},{P['hi']:+.4f}] p={P['p']:.3f}; Hit {int(hit['hybrid_no_floor'].sum())}->{int(hit[n].sum())}/{len(ids)}; empty answerable {int(emp['hybrid_no_floor'].sum())}->{int(emp[n].sum())}")
        n50='floor_0.50'; P=pb(nd[n50]-nd['hybrid_no_floor']); print(f"  at f=0.50: nDCG {nd[n50].mean():.3f} d={P['diff']:+.4f} [{P['lo']:+.4f},{P['hi']:+.4f}]; empty answerable {int(emp[n50].sum())}; Hit {int(hit[n50].sum())}/{len(ids)}")
        rng=np.random.default_rng(0); cnt={}
        for _ in range(5000):
            idx=rng.integers(0,100,100); k=str(choose(H[idx])); cnt[k]=cnt.get(k,0)+1
        print('  bootstrap-5000 f* shares',{k:round(v/5000,3) for k,v in sorted(cnt.items())})
    # prefix - raw paired
    for n in ('hybrid_no_floor','vector_only','bm25_only'):
        P=pb(res['prefix']['nd'][n]-res['raw']['nd'][n]); print(f"  prefix - raw {n}: {P['diff']:+.3f} [{P['lo']:+.3f},{P['hi']:+.3f}] p={P['p']:.4f}")
