import json,sys,numpy as np
sys.path.insert(0,'.')
from evaluation import stats
def W(k,n):
    lo,hi=stats.wilson(k,n); return f'{k/n:.3f} [{lo:.3f},{hi:.3f}] ({k}/{n})'
def boot(d,seed=0,B=10000):
    d=np.asarray(d,float); rng=np.random.default_rng(seed); m=d[rng.integers(0,len(d),(B,len(d)))].mean(1)
    return d.mean(),*np.percentile(m,[2.5,97.5])
for m in ['llama3-latest','qwen2.5-7b']:
    d=json.load(open(f'paper/results/endtoend-{m}.json',encoding='utf8'))
    G={g:{(r['kind'],r['id']):r for r in v['records']} for g,v in d['gates'].items()}
    print('=======',m)
    for g in G:
        recs=list(G[g].values())
        fq=[r for r in recs if r['kind']=='fiqa']; sc=[r for r in recs if r['kind']=='scifact']
        gate_empty_fq=sum(r['retrieved_none'] for r in fq); 
        modelref_fq=sum(r['refused'] and not r['retrieved_none'] for r in fq)
        ans_fq=sum(not r['refused'] for r in fq)
        print(g,'| FiQA refused',W(sum(r['refused'] for r in fq),100),'gate-empty',gate_empty_fq,'model-refused',modelref_fq,'answered (non-refusal)',ans_fq,
              '| SciFact refused',W(sum(r['refused'] for r in sc),100),'gate-empty',sum(r['retrieved_none'] for r in sc),'supported',W(sum(r['supported'] for r in sc),100),
              'retr_rel',W(sum(r['retrieved_relevant'] for r in sc),100),
              '| ms mean/med/p95 FiQA',np.mean([r['ms'] for r in fq]).round(0),np.median([r['ms'] for r in fq]),np.percentile([r['ms'] for r in fq],95).round(0),
              'SciFact',np.mean([r['ms'] for r in sc]).round(0),np.median([r['ms'] for r in sc]),np.percentile([r['ms'] for r in sc],95).round(0),
              'all mean',np.mean([r['ms'] for r in recs]).round(0),'median',np.median([r['ms'] for r in recs]))
    base=G['no_floor']
    for g in ('floor_0.50','floor_0.60'):
        print('--',g,'vs no_floor (paired by item)')
        for kind,key,label in [('fiqa','refused','FiQA refused'),('scifact','refused','SciFact refused'),('scifact','supported','SciFact supported'),('scifact','retrieved_relevant','SciFact retrieved_relevant')]:
            ks=[k for k in base if k[0]==kind]
            w=sum(1 for k in ks if G[g][k][key] and not base[k][key]); l=sum(1 for k in ks if not G[g][k][key] and base[k][key])
            print(f'  {label}: floor-only {w}, nofloor-only {l}, McNemar p={stats.mcnemar_exact(w,l):.4f}')
        # retrieved docs changed
        for kind in ('fiqa','scifact'):
            ks=[k for k in base if k[0]==kind]
            ch=sum(G[g][k]['retrieved']!=base[k]['retrieved'] for k in ks)
            print(f'  {kind}: items whose retrieved list changed {ch}/100; became empty {sum(G[g][k]["retrieved_none"] and not base[k]["retrieved_none"] for k in ks)}')
        for kind in ('fiqa','scifact'):
            ks=[k for k in base if k[0]==kind]
            dd=[G[g][k]['ms']-base[k]['ms'] for k in ks]
            print(f'  {kind} latency diff (floor-nofloor) ms paired boot: mean/lo/hi',[round(x) for x in boot(dd)])
        ks=list(base); dd=[G[g][k]['ms']-base[k]['ms'] for k in ks]; print('  all latency diff',[round(x) for x in boot(dd)])
        # answer text identical when same retrieval
        same=[k for k in base if G[g][k]['retrieved']==base[k]['retrieved']]
        print('  same retrieval items',len(same),'identical answers',sum(G[g][k]['answer']==base[k]['answer'] for k in same))
    # FiQA answered-but-no-gate examples
    fq=[r for r in base.values() if r['kind']=='fiqa' and not r['refused']]
    print('FiQA non-refused at no_floor:',[(r['query'][:70],r['answer'][:90]) for r in fq][:6])
    # scifact refusals despite relevant retrieved
    sc=[r for r in base.values() if r['kind']=='scifact']
    print('SciFact retrieved relevant but refused:',sum(r['retrieved_relevant'] and r['refused'] for r in sc),'; retrieved nothing relevant & refused',sum((not r['retrieved_relevant']) and r['refused'] for r in sc),'; retrieved relevant & answered', sum(r['retrieved_relevant'] and not r['refused'] for r in sc),'; no relevant & answered',sum((not r['retrieved_relevant']) and not r['refused'] for r in sc))
    # error/ambiguity
    print('errors',sum(bool(r['error']) for g in G for r in G[g].values()))
