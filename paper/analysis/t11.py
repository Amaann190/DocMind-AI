import json,itertools,numpy as np
for m in ['llama3.2-3b','qwen2.5-7b','llama3-latest','qwen2.5-3b']:
    runs=[json.load(open(f'output/research/answers-{m}-full{s}.json',encoding='utf8')) for s in ('','-r1','-r2')]
    R=[{r['id']:r for r in d['records']} for d in runs]
    ids=list(R[0]); assert all(list(x)==ids for x in R)
    print('==',m,'| meta',[(d.get('temperature'),d.get('seed'),d.get('repeat'),d['generated']) for d in runs])
    for a,b in ((0,1),(0,2),(1,2)):
        same=sum(R[a][i]['answer']==R[b][i]['answer'] for i in ids)
        gr=sum(bool(R[a][i]['correct'])==bool(R[b][i]['correct']) for i in ids)
        ref=sum(bool(R[a][i]['refused'])==bool(R[b][i]['refused']) for i in ids)
        src=sum(R[a][i]['sources']!=R[b][i]['sources'] for i in ids); pas=sum(R[a][i]['passages']!=R[b][i]['passages'] for i in ids)
        print(f'  r{a} vs r{b}: identical answers {same}/200; strict-grade agreement {gr}/200; refusal-flag agreement {ref}/200; sources differ {src}; passages differ {pas}')
    all3=sum(R[0][i]['answer']==R[1][i]['answer']==R[2][i]['answer'] for i in ids)
    print(f'  identical in all three: {all3}/200 ; grade identical all three {sum(len({bool(R[k][i]["correct"]) for k in range(3)})==1 for i in ids)}/200')
    ac=[sum(R[k][i]['correct'] for i in ids if not R[k][i]['unanswerable']) for k in range(3)]; ua=[sum(R[k][i]['correct'] for i in ids if R[k][i]['unanswerable']) for k in range(3)]
    print(f'  answerable-correct per run {ac} (range {max(ac)-min(ac)}); unanswerable-abstain per run {ua} (range {max(ua)-min(ua)}); overall {[a+u for a,u in zip(ac,ua)]}')
    print('  mean f1',[round(d['summary']['answerable_mean_f1'],4) for d in runs],'mean_ms',[round(d['summary']['mean_ms']) for d in runs],'cited',[d['summary']['answered_with_citation'] for d in runs])
    # kinds of differences among differing
    diff=[i for i in ids if len({R[k][i]['answer'] for k in range(3)})>1]
    print('  items with any string difference:',len(diff),'(answerable',sum(not R[0][i]['unanswerable'] for i in diff),', unanswerable',sum(R[0][i]['unanswerable'] for i in diff),')')
    # differing items by length ratio
    import difflib
    sims=[min(difflib.SequenceMatcher(None,R[0][i]['answer'],R[k][i]['answer']).ratio() for k in (1,2)) for i in diff]
    print('  min similarity among differing (median/min):',round(float(np.median(sims)),3) if sims else None,round(min(sims),3) if sims else None)
    # injection too
    inj=[[ (x['id'],x['filter'],x['answer']) for x in d['injection']] for d in runs]
    print('  injection answers identical r0=r1',sum(a==b for a,b in zip(inj[0],inj[1])),'/',len(inj[0]),' r0=r2',sum(a==b for a,b in zip(inj[0],inj[2])),'; injection n',len(inj[0]) )
