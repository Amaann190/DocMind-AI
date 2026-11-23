import json,sys,numpy as np
sys.path.insert(0,'.')
from evaluation import beir
# subset check
off300=beir.sample(beir.load_split(beir.ensure_beir('fiqa'),'test')[0],300)
off100=beir.sample(beir.load_split(beir.ensure_beir('fiqa'),'test')[0],100,13)
sw=json.load(open('paper/results/sweep-scifact-nomic-embed-text-latest.json',encoding='utf8'))['rows']['offtopic']
print('sweep offtopic keys == sample300:',list(sw)==list(off300),len(sw),'| endtoend100 subset of sweep300:',set(off100)<=set(sw),'| first100 of sweep order equal:',list(off100)==list(sw)[:100])
for m in ['llama3-latest','qwen2.5-7b']:
    d=json.load(open(f'paper/results/endtoend-{m}.json',encoding='utf8'))
    print('=====',m,{k:d[k] for k in d if k not in('gates',)},'gate order',list(d['gates']))
    ids=[r['id'] for r in d['gates']['no_floor']['records']]; 
    for g in d['gates']: assert [r['id'] for r in d['gates'][g]['records']]==ids
    fq_ids=set(i for i in ids if i.startswith('fiqa_')); print('e2e fiqa ids subset of sweep',all(i[5:] in sw or i in sw for i in fq_ids), list(sw)[:2],list(fq_ids)[:2])
    G={g:{r['id']:r for r in v['records']} for g,v in d['gates'].items()}
    base=G['no_floor']
    for g in ('floor_0.60','floor_0.50'):
        print(f'--- {g} vs no_floor')
        for kind in ('fiqa','scifact'):
            ks=[i for i in base if base[i]['kind']==kind]
            chg=sum(G[g][i]['answer']!=base[i]['answer'] for i in ks)
            retchg=sum(G[g][i]['retrieved']!=base[i]['retrieved'] for i in ks)
            same_ret_chg=sum(G[g][i]['answer']!=base[i]['answer'] and G[g][i]['retrieved']==base[i]['retrieved'] for i in ks)
            a2d=sum((not base[i]['refused']) and G[g][i]['refused'] for i in ks); d2a=sum(base[i]['refused'] and not G[g][i]['refused'] for i in ks)
            toempty=sum(G[g][i]['retrieved_none'] and not base[i]['retrieved_none'] for i in ks); 
            ans2empty=sum((not base[i]['refused']) and G[g][i]['retrieved_none'] for i in ks)
            ref_base=sum(base[i]['refused'] for i in ks); ref_g=sum(G[g][i]['refused'] for i in ks)
            print(f" {kind}: changed answer strings {chg}/100 (retrieval changed {retchg}; changed despite identical retrieval {same_ret_chg}); refused no_floor {ref_base} -> {g} {ref_g}; answered->declined {a2d}; declined->answered {d2a}; ->empty retrieval {toempty} (of which previously answered {ans2empty}); gate-empty total {sum(G[g][i]['retrieved_none'] for i in ks)}, no_floor empty {sum(base[i]['retrieved_none'] for i in ks)}")
            if kind=='scifact':
                sup=lambda r: (not r['refused']) and bool(r['cites_relevant'])
                s2n=sum(sup(base[i]) and not sup(G[g][i]) for i in ks); n2s=sum((not sup(base[i])) and sup(G[g][i]) for i in ks)
                print(f"   SciFact supported(non-refusal citing qrel doc): no_floor {sum(sup(base[i]) for i in ks)} -> {sum(sup(G[g][i]) for i in ks)}; lost {s2n}, gained {n2s}; retrieved_relevant {sum(base[i]['retrieved_relevant'] for i in ks)}->{sum(G[g][i]['retrieved_relevant'] for i in ks)}")
    print('--- per-gate latency ms mean (FiQA / SciFact) and calls avoided /200')
    for g in d['gates']:
        fq=[r for r in G[g].values() if r['kind']=='fiqa']; sc=[r for r in G[g].values() if r['kind']=='scifact']; al=list(G[g].values())
        print(f" {g}: FiQA {np.mean([r['ms'] for r in fq]):.0f} (refused {sum(r['refused'] for r in fq)}, empty {sum(r['retrieved_none'] for r in fq)}) | SciFact {np.mean([r['ms'] for r in sc]):.0f} (refused {sum(r['refused'] for r in sc)}, empty {sum(r['retrieved_none'] for r in sc)}, supported {sum((not r['refused']) and bool(r['cites_relevant']) for r in sc)}) | all {np.mean([r['ms'] for r in al]):.0f} | calls avoided {sum(r['retrieved_none'] for r in al)}/200 | errors {sum(bool(r['error']) for r in al)}")
    # latency for items with identical retrieval (drift check)
    for g in ('floor_0.60','floor_0.50'):
        same=[i for i in base if G[g][i]['retrieved']==base[i]['retrieved'] and not base[i]['retrieved_none']]
        print(f" drift check {g}: items with identical non-empty retrieval {len(same)}: mean ms gate {np.mean([G[g][i]['ms'] for i in same]):.0f} vs no_floor {np.mean([base[i]['ms'] for i in same]):.0f}; identical answers {sum(G[g][i]['answer']==base[i]['answer'] for i in same)}")
