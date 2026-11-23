import json,csv,sys,numpy as np
sys.path.insert(0,'.')
from evaluation import stats,squad
SP=r"paper/analysis/"
A=json.load(open(SP+'taskA.json'))
adj=list(csv.DictReader(open(SP+"squad_adjudication.csv",encoding="utf-8-sig"))); rel=[x['id'] for x in adj if x['label'].startswith('answerable')]
ALT_MAN={'llama3.2-3b':[1,0,1,1,0,1,1,1,1],'qwen2.5-7b':[1,1,1,1,0,1,1,1,1],'llama3-latest':[1,1,1,1,0,1,1,1,1],'qwen2.5-3b':[1,0,0,1,1,0,0,1,1]}
Wl=lambda k,n:'%.3f (%d/%d)'%(k/n,k,n)
def mc(x,y,ids):
    w=sum(1 for i in ids if x[i] and not y[i]); l=sum(1 for i in ids if y[i] and not x[i]); return w,l,stats.mcnemar_exact(w,l)
for m in ['llama3.2-3b','qwen2.5-7b','llama3-latest','qwen2.5-3b']:
    D=json.load(open(f'paper/results/answers-{m}-full.json',encoding='utf8')); E=json.load(open(f'paper/results/answers-{m}-full-alt.json',encoding='utf8'))
    Dr={r['id']:r for r in D['records']}; Er={r['id']:r for r in E['records']}
    assert list(Dr)==list(Er)
    una={i for i,r in Dr.items() if r['unanswerable']}; ans=[i for i in Dr if i not in una]; un=[i for i in Dr if i in una]
    dorig={i:int(bool(r['correct'])) for i,r in Dr.items()}; eorig={i:int(bool(r['correct'])) for i,r in Er.items()}
    dadj=dict(A[m]['adj']); eadj=dict(eorig)
    for i,g in zip(rel,ALT_MAN[m]): eadj[i]=g
    ans_c=ans+rel; un_c=[i for i in un if i not in rel]
    out=[]
    for lab,(dd,ee,aa,uu) in {'orig':(dorig,eorig,ans,un),'corrected':(dadj,eadj,ans_c,un_c)}.items():
        for nm,ids in (('answerable-correct',aa),('unanswerable-abstain',uu)):
            kd=sum(dd[i] for i in ids); ke=sum(ee[i] for i in ids); w,l,p=mc(ee,dd,ids)
            out.append(f"  {lab:9s} {nm:21s}: default {Wl(kd,len(ids))} | alt {Wl(ke,len(ids))} | alt-only {w}, default-only {l} | McNemar p={p:.4f}")
    print('==',m); print('\n'.join(out))
    # lenient/refusal rates
    print('  refusal rate (strict) answerable: default %d alt %d | unanswerable: default %d alt %d'%(sum(Dr[i]['refused'] for i in ans),sum(Er[i]['refused'] for i in ans),sum(Dr[i]['refused'] for i in un),sum(Er[i]['refused'] for i in un)))
    sd,se=D['summary'],E['summary']
    print('  citation (cited among non-refused): default %s alt %s | all answers cited incl refusals: default %d/200 alt %d/200'%(Wl(sd['answered_with_citation']['k'],sd['answered_with_citation']['n']),Wl(se['answered_with_citation']['k'],se['answered_with_citation']['n']),sum(r['cited'] for r in Dr.values()),sum(r['cited'] for r in Er.values())))
    print('  mean ms/question default %.0f alt %.0f | run seconds default %s alt %s | mean f1 %.3f -> %.3f | overall correct orig %d -> %d'%(sd['mean_ms'],se['mean_ms'],D['seconds'],E['seconds'],sd['answerable_mean_f1'],se['answerable_mean_f1'],sd['overall_correct']['k'] if isinstance(sd['overall_correct'],dict) else sd['overall_correct'],se['overall_correct']['k'] if isinstance(se['overall_correct'],dict) else se['overall_correct']))
    # identical answer strings and retrieval
    print('  identical answer strings default vs alt: %d/200; sources differ %d'%(sum(Dr[i]['answer']==Er[i]['answer'] for i in Dr),sum(Dr[i]['sources']!=Er[i]['sources'] for i in Dr)))
    # injection
    for tag,dd in (('default',D),('alt',E)):
        inj=dd['injection']; 
        on=[x for x in inj if x['filter']]; off=[x for x in inj if not x['filter']]
        print(f"  injection {tag}: filter on attack success {sum(x['attack_success'] for x in on)}/{len(on)}, off {sum(x['attack_success'] for x in off)}/{len(off)}; task success on {sum(x['task_success'] for x in on)}/{len(on)}")
    # response length
    print('  mean answer chars default %.0f alt %.0f'%(np.mean([len(r['answer']) for r in Dr.values()]),np.mean([len(r['answer']) for r in Er.values()])))
