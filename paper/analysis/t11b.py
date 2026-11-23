import json
S={}
for m in ['llama3.2-3b','qwen2.5-7b','llama3-latest','qwen2.5-3b']:
    a=json.load(open(f'paper/results/answers-{m}-full.json',encoding='utf8'))['records']; b=json.load(open(f'paper/results/answers-{m}-full-r1.json',encoding='utf8'))['records']
    d=[(x['id'],x['unanswerable'],x['sources'],y['sources']) for x,y in zip(a,b) if x['sources']!=y['sources']]
    S[m]=d
    for i,u,s0,s1 in d: print(m,i[-6:],'una' if u else 'ans',s0,'->',s1)
    # answers that differ with identical sources: fraction
    n=sum(x['answer']!=y['answer'] and x['sources']==y['sources'] for x,y in zip(a,b)); print('  differing answers with identical sources',n)
    # sample diffs
    k=0
    for x,y in zip(a,b):
        if x['answer']!=y['answer'] and x['sources']==y['sources'] and len(x['answer'])<150 and k<1: print('  EX r0:',x['answer'][:150].replace('\n',' '),'\n     r1:',y['answer'][:150].replace('\n',' ')); k+=1
print('same ids across models', len({tuple(i for i,_,_,_ in v) for v in S.values()}))
