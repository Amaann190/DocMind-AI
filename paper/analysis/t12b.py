import json,sys
sys.path.insert(0,'.')
from evaluation import stats
for m in ['llama3.2-3b','qwen2.5-7b','llama3-latest','qwen2.5-3b']:
    R={r['id']:r for r in json.load(open(f'output/research/answers-{m}-full-r1.json',encoding='utf8'))['records']}
    E={r['id']:r for r in json.load(open(f'output/research/answers-{m}-full-alt.json',encoding='utf8'))['records']}
    s=[]
    for nm,flag in (('ans',False),('una',True)):
        ids=[i for i in R if R[i]['unanswerable']==flag]
        w=sum(1 for i in ids if E[i]['correct'] and not R[i]['correct']); l=sum(1 for i in ids if R[i]['correct'] and not E[i]['correct'])
        s.append(f"{nm}: r1 {sum(R[i]['correct'] for i in ids)} alt {sum(E[i]['correct'] for i in ids)} (alt-only {w}, r1-only {l}, p={stats.mcnemar_exact(w,l):.3f})")
    print(m,' | '.join(s),'| identical strings r1 vs alt',sum(R[i]['answer']==E[i]['answer'] for i in R),'/200 | cited r1',sum(r['cited'] for r in R.values()),'alt',sum(r['cited'] for r in E.values()))
