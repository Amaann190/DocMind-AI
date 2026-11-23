import json,sys,numpy as np
sys.path.insert(0,'.')
SP=r"paper/analysis/"
A=json.load(open(SP+'taskA.json'))
import csv
adj=list(csv.DictReader(open(SP+"squad_adjudication.csv",encoding="utf-8-sig"))); rel={x['id'] for x in adj if x['label'].startswith('answerable')}
d=json.load(open('paper/results/answers-llama3.1-8b-full.json',encoding='utf8'))['records']
title={r['id']:r['title'] for r in d}; una={r['id'] for r in d if r['unanswerable']}
arts=sorted(set(title.values())); print('articles',len(arts)); aidx={a:i for i,a in enumerate(arts)}
cl=np.array([aidx[title[r['id']]] for r in d]); ids=[r['id'] for r in d]
# check context_id article prefix agrees
cp=set(r['context_id'].rsplit('_',1)[0] for r in d); print('context article prefixes',len(cp))
def vec(m,lab):
    return np.array([A[m][lab][i] for i in ids],float)
def subset(kind,lab):
    s=np.zeros(len(ids),bool)
    for j,i in enumerate(ids):
        if kind=='ans': s[j]= (i not in una) or (lab=='adj' and i in rel)
        elif kind=='una': s[j]= (i in una) and not (lab=='adj' and i in rel)
        else: s[j]=True
    return s
rng=np.random.default_rng(0); B=10000
samp=rng.integers(0,len(arts),size=(B,len(arts)))
def cb(a,b,kind,lab):
    s=subset(kind,lab); va=vec(a,lab); vb=vec(b,lab)
    num=np.array([ (va[s&(cl==g)]-vb[s&(cl==g)]).sum() for g in range(len(arts))]); den=np.array([ (s&(cl==g)).sum() for g in range(len(arts))],float)
    est=num.sum()/den.sum()
    # for unanswerable abstain under 'orig', vec orig is correct=refused. ok
    bs=num[samp].sum(1)/den[samp].sum(1)
    lo,hi=np.percentile(bs,[2.5,97.5]); p=min(1,2*(min((bs<=0).sum(),(bs>=0).sum())+1)/(B+1))
    # iid bootstrap for comparison
    idx=np.where(s)[0]; dd=(va-vb)[idx]; r2=np.random.default_rng(1); m=dd[r2.integers(0,len(dd),(B,len(dd)))].mean(1)
    return est,lo,hi,p,int(s.sum()),np.percentile(m,[2.5,97.5]),int(va[s].sum()),int(vb[s].sum())
pairs=[('qwen2.5-3b','llama3.2-3b'),('llama3.1-8b','qwen2.5-7b'),('llama3.2-1b','qwen2.5-1.5b'),('llama3.1-8b','llama3-latest')]
print('| pair | endpoint | labels | n | k_a | k_b | delta (pp) | cluster 95% CI | p | iid 95% CI |')
for a,b in pairs:
    for kind in ('ans','una'):
        for lab in ('orig','adj'):
            est,lo,hi,p,n,iid,ka,kb=cb(a,b,kind,lab)
            print(f"| {a} vs {b} | {'answerable-correct' if kind=='ans' else 'unanswerable-abstain'} | {'orig' if lab=='orig' else 'corrected'} | {n} | {ka:.0f} | {kb:.0f} | {est*100:+.1f} | [{lo*100:+.1f},{hi*100:+.1f}] | {p:.3f} | [{iid[0]*100:+.1f},{iid[1]*100:+.1f}] |")
print('--- size steps (overall correct, corrected labels, n=200)')
steps=[('qwen2.5-1.5b','qwen2.5-0.5b'),('qwen2.5-3b','qwen2.5-1.5b'),('qwen2.5-7b','qwen2.5-3b'),('qwen2.5-7b','qwen2.5-0.5b'),('llama3.2-3b','llama3.2-1b'),('llama3.1-8b','llama3.2-3b'),('llama3.1-8b','llama3.2-1b')]
for a,b in steps:
    for kind in ('all',):
        for lab in ('adj',):
            est,lo,hi,p,n,iid,ka,kb=cb(a,b,kind,lab)
            print(f"| {a} - {b} | overall corrected | {n} | {ka:.0f} vs {kb:.0f} | {est*100:+.1f} | [{lo*100:+.1f},{hi*100:+.1f}] | p={p:.3f} | iid [{iid[0]*100:+.1f},{iid[1]*100:+.1f}]")
# also items per article distribution
cnt=np.bincount(cl); print('items/article min/med/max',cnt.min(),np.median(cnt),cnt.max())
