import sys; sys.path.insert(0,r"paper/analysis")
from common_sw import *
FLOORS=[0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7]
EMB={'nomic':'nomic-embed-text-latest','minilm':'all-minilm-latest'}
HELD={'scifact':('scifact-train','train'),'nfcorpus':('nfcorpus-dev','dev')}
out={}
for ds,(pref,split) in HELD.items():
    hq=qrels_for(ds,split); tq=qrels_for(ds,'test')
    for e,ef in EMB.items():
        hd=load(f'sweep-{pref}-{ef}-plain-kw2.json'); td=load(f'sweep-{ds}-{ef}-plain-kw2.json')
        for kw in ('', 'kw2_'):
            names=[f'{kw}hybrid_no_floor']+[f'{kw}floor_{f:.2f}' for f in FLOORS]
            hrows={q:r for q,r in hd['rows']['test'].items() if q in hq}
            hpq=per_query(hrows,hq,names)
            # 100-sample calib used in the test sweep
            crows=td['rows']['calib']; ccal=qrels_for(ds,{'scifact':'train','nfcorpus':'dev'}[ds])
            cpq=per_query(crows,ccal,names)
            def choose(pq,tol,metric='hit'):
                ref=pq[names[0]][metric].mean()
                q=[f for f,n in zip(FLOORS,names[1:]) if pq[n][metric].mean()>=tol*ref]
                return max(q) if q else None
            res={}
            res['n_held']=len(hrows); res['n_calib100']=len(crows)
            res['curve_full']={n:round(float(hpq[n]['hit'].mean()),4) for n in names}
            res['curve_100']={n:round(float(cpq[n]['hit'].mean()),4) for n in names}
            res['fstar_full']={str(t):choose(hpq,t) for t in (0.95,0.97,0.98,0.99)}
            res['fstar_full_recall']={str(t):choose(hpq,t,'rec') for t in (0.95,0.97,0.98,0.99)}
            res['fstar_100']={str(t):choose(cpq,t) for t in (0.95,0.97,0.98,0.99)}
            # bootstrap stability on full held-out
            rng=np.random.default_rng(0); cnt={}
            H=np.stack([hpq[n]['hit'] for n in names]); 
            for _ in range(2000):
                idx=rng.integers(0,H.shape[1],H.shape[1]); m=H[:,idx].mean(1)
                q=[f for f,v in zip(FLOORS,m[1:]) if v>=0.98*m[0]]; c=str(max(q) if q else None); cnt[c]=cnt.get(c,0)+1
            res['fstar_boot2000']=dict(sorted(cnt.items()))
            # test
            tspq=per_query(td['rows']['test'],tq,[n for n in td['rows']['test'][next(iter(td['rows']['test']))] if n!='query'])
            tn=list(tspq)
            res['test_file_cal']=td['summary'].get('calibrated_floor')
            fs=res['fstar_full']['0.98']; f100=res['fstar_100']['0.98']
            def cfg(n):
                if n is None: return None
                v=tspq[n]; off=td['rows']['offtopic']
                rej=sum(1 for r in off.values() if not r[n])
                return dict(ndcg=float(v['ndcg'].mean()),hit=float(v['hit'].mean()),rec=float(v['rec'].mean()),empty=float(v['empty'].mean()),docs=float(v['docs'].mean()),fiqa=wil(rej,len(off)))
            test={}
            test['no_floor']=cfg(f'{kw}hybrid_no_floor'); test['default0.5']=cfg(f'{kw}floor_0.50')
            test['heldout_fstar']=cfg(f'{kw}floor_{fs:.2f}') if fs else None
            test['cal100_fstar']=cfg(f'{kw}floor_{f100:.2f}') if f100 else None
            bestn=max([f'{kw}floor_{f:.2f}' for f in FLOORS],key=lambda n:tspq[n]['ndcg'].mean()); test['oracle_best_test_ndcg_floor']=(bestn,float(tspq[bestn]['ndcg'].mean()))
            res['test']=test
            P={}
            if fs: P['heldout_vs_nofloor']=pb(tspq[f'{kw}floor_{fs:.2f}']['ndcg']-tspq[f'{kw}hybrid_no_floor']['ndcg'])
            if fs: P['heldout_vs_default']=pb(tspq[f'{kw}floor_{fs:.2f}']['ndcg']-tspq[f'{kw}floor_0.50']['ndcg'])
            if f100 and f100!=fs: P['cal100_vs_nofloor']=pb(tspq[f'{kw}floor_{f100:.2f}']['ndcg']-tspq[f'{kw}hybrid_no_floor']['ndcg'])
            if fs and f100 and fs!=f100: P['heldout_vs_cal100']=pb(tspq[f'{kw}floor_{fs:.2f}']['ndcg']-tspq[f'{kw}floor_{f100:.2f}']['ndcg'])
            P['default_vs_nofloor']=pb(tspq[f'{kw}floor_0.50']['ndcg']-tspq[f'{kw}hybrid_no_floor']['ndcg'])
            res['paired']=P
            # full test nDCG curve and fiqa curve
            res['test_curve']={n:(round(float(tspq[n]['ndcg'].mean()),3),round(float(tspq[n]['empty'].mean()),3),round(sum(1 for r in td['rows']['offtopic'].values() if not r[n])/300,3)) for n in names}
            out[f'{ds}|{e}|{kw or "kw1"}']=res
import pprint
for k,v in out.items():
    print('=====',k); 
    for kk,vv in v.items(): print(' ',kk,':',vv)
json.dump(out,open(r"paper/analysis/taskD.json",'w'),indent=1,default=str)
