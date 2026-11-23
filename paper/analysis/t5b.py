import json
for m in ['qwen2.5-1.5b','llama3.2-3b','llama3-latest']:
    on=json.load(open(f'paper/results/resources-{m}-eco-on.json',encoding='utf8')); off=json.load(open(f'paper/results/resources-{m}-eco-off.json',encoding='utf8'))
    B={r['id']:r for r in off['records']}
    for r in on['records']:
        if r['prompt_tokens']<B[r['id']]['prompt_tokens']: print(m,r['id'],r['unanswerable'],r['prompt_tokens'],B[r['id']]['prompt_tokens'], 'ans changed',r['answer']!=B[r['id']]['answer'],'| correct on/off',r['correct'],B[r['id']]['correct'])
        if r['answer']!=B[r['id']]['answer']: print('  ON :',r['answer'][:200].replace('\n',' '),'\n  OFF:',B[r['id']]['answer'][:200].replace('\n',' '))
