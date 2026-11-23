import json,csv,sys
sys.path.insert(0,'.')
from evaluation import squad
SP=r"paper/analysis/"
adj=list(csv.DictReader(open(SP+"squad_adjudication.csv",encoding="utf-8-sig")))
rel=[x for x in adj if x['label'].startswith('answerable')]
A=json.load(open(SP+'taskA.json'))
for x in rel:
    print('###',x['id'][-6:],x['question'],'| gold:',x['gold_answer'],'| quote:',x['evidence_quote'][:200])
    for m in ['llama3.2-3b','qwen2.5-7b','llama3-latest','qwen2.5-3b']:
        d={r['id']:r for r in json.load(open(f'output/research/answers-{m}-full.json',encoding='utf8'))['records']}
        e={r['id']:r for r in json.load(open(f'output/research/answers-{m}-full-alt.json',encoding='utf8'))['records']}
        i=x['id']
        print(f'  [{m}] default adj={A[m]["adj"][i]} :',d[i]['answer'][:160].replace('\n',' '))
        print(f'  [{m}] ALT strict_refused={e[i]["refused"]} contains_gold_str={squad.contains_gold(e[i]["answer"],[x["gold_answer"]])} :',e[i]['answer'][:260].replace('\n',' '))
