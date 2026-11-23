import json,csv,sys,itertools
sys.path.insert(0,'.')
from evaluation import squad, stats
adj=list(csv.DictReader(open(r"paper/squad_adjudication.csv",encoding="utf-8-sig")))
rel=[x['id'] for x in adj if x['label'].startswith('answerable')]
ids5=[x['id'] for x in adj if x['label'].startswith('answerable')]
# manual grades for new models, order of rel ids
order=['0e18e0','428eec','0e18d8','0024b0','42a0ae','429930','686fc3','922344','2eb73d']
assert [i[-6:] for i in rel]==order,[i[-6:] for i in rel]
manual={'qwen2.5-3b':[1,0,0,1,1,1,1,1,1],'llama3.2-1b':[1,1,0,0,1,1,1,0,0],'llama3.1-8b':[1,1,1,1,0,1,1,0,1]}
models=['qwen2.5-0.5b','qwen2.5-1.5b','qwen2.5-3b','qwen2.5-7b','llama3.2-1b','llama3.2-3b','llama3.1-8b','llama3-latest']
oldman={}
for x in adj:
    if x['label'].startswith('answerable'):
        for m in ['qwen2.5-0.5b','qwen2.5-1.5b','llama3.2-3b','qwen2.5-7b','llama3-latest']:
            oldman.setdefault(m,[]).append(int(x[m+'_new_correct']))
manual.update(oldman)
out={}
idsets=set()
for m in models:
    d=json.load(open(f'output/research/answers-{m}-full.json',encoding='utf8'))
    recs=d['records']; idsets.add(tuple(r['id'] for r in recs))
    # verify grading reproducible
    item=lambda r:{'unanswerable':r['unanswerable'],'answers':r['answers']}
    chk=sum(squad.grade(item(r),r['answer'])!=r['correct'] for r in recs)
    orig={r['id']:int(bool(r['correct'])) for r in recs}
    ref={r['id']:bool(r['refused']) for r in recs}
    una=[r for r in recs if r['unanswerable']]; ans=[r for r in recs if not r['unanswerable']]
    adjd=dict(orig)
    for i,g in zip(rel,manual[m]): adjd[i]=g
    out[m]=dict(orig=orig,adj=adjd,n_ans=len(ans),n_una=len(una),regrade_mismatch=chk,
                temp=d['temperature'],emb=d['embedding'],f1=d['summary'].get('answerable_mean_f1'),
                gold_ret=d['summary']['answerable_retrieved_gold']['k'])
print('same ids/order across models:',len(idsets)==1)
unaset={r['id'] for r in json.load(open('output/research/answers-llama3.1-8b-full.json',encoding='utf8'))['records'] if r['unanswerable']}
ansset=None
def W(k,n):
    lo,hi=stats.wilson(k,n); return f'{k/n:.3f} [{lo:.3f},{hi:.3f}] ({k}/{n})'
print('== table')
for m in models:
    o=out[m]; 
    a=sum(v for i,v in o['orig'].items() if i not in unaset); u=sum(v for i,v in o['orig'].items() if i in unaset)
    rel_set=set(rel)
    a2=a+sum(o['adj'][i] for i in rel); u2=sum(v for i,v in o['adj'].items() if i in unaset and i not in rel_set)
    # also: of the 9 relabelled, how many "abstained" (refused) vs answered
    print(f"{m} | orig ans {W(a,100)} | orig unans-refused {W(u,100)} | adj ans {W(a2,109)} | adj unans-abstain {W(u2,91)} | overall orig {W(a+u,200)} | overall adj {W(a2+u2,200)} | regradeMismatch {o['regrade_mismatch']} f1={o['f1']:.3f} goldret={o['gold_ret']}")
print('== relabelled 9: correct count orig-refused vs adj')
for m in models:
    o=out[m]; print(m,'refused-as-orig-correct',sum(o['orig'][i] for i in rel),'adj-correct',sum(o['adj'][i] for i in rel))
pairs=[('qwen2.5-3b','llama3.2-3b'),('llama3.1-8b','qwen2.5-7b'),('llama3.1-8b','llama3-latest'),('llama3.2-1b','qwen2.5-1.5b'),('llama3.2-1b','qwen2.5-0.5b'),('qwen2.5-7b','llama3-latest'),('llama3.2-3b','qwen2.5-7b'),('llama3.2-3b','llama3-latest')]
def mc(a,b,key,subset):
    w=sum(1 for i in subset if out[a][key][i] and not out[b][key][i]); l=sum(1 for i in subset if not out[a][key][i] and out[b][key][i])
    return w,l,stats.mcnemar_exact(w,l)
allids=list(out[models[0]]['orig'])
sets={'all200':allids,'answerable100':[i for i in allids if i not in unaset],'unanswerable100':[i for i in allids if i in unaset]}
for key in ('orig','adj'):
    print('== McNemar',key,'(a wins=a correct,b wrong ; a loses) ')
    for a,b in pairs:
        s=[]
        for sn,ss in sets.items():
            w,l,p=mc(a,b,key,ss); s.append(f'{sn}: {w}/{l} p={p:.4f}')
        print(f'{a} vs {b}: '+' | '.join(s))
json.dump({m:{'orig':o['orig'],'adj':o['adj']} for m,o in out.items()},open(r"paper/analysis/taskA.json",'w'))
