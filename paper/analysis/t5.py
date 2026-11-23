import json,numpy as np
for m in ['qwen2.5-1.5b','llama3.2-3b','llama3-latest']:
    on=json.load(open(f'output/research/resources-{m}-eco-on.json',encoding='utf8')); off=json.load(open(f'output/research/resources-{m}-eco-off.json',encoding='utf8'))
    A={r['id']:r for r in on['records']}; B={r['id']:r for r in off['records']}
    assert list(A)==list(B)
    ids=list(A); n=len(ids)
    pt_on=np.array([A[i].get('prompt_tokens') or 0 for i in ids]); pt_off=np.array([B[i].get('prompt_tokens') or 0 for i in ids])
    called=[i for i in ids if A[i].get('prompt_tokens') and B[i].get('prompt_tokens')]
    shorter=[i for i in called if A[i]['prompt_tokens']<B[i]['prompt_tokens']]
    longer=[i for i in called if A[i]['prompt_tokens']>B[i]['prompt_tokens']]
    eq=[i for i in called if A[i]['prompt_tokens']==B[i]['prompt_tokens']]
    changed=[i for i in ids if A[i]['answer']!=B[i]['answer']]
    ec_on=[A[i].get('eval_count') or 0 for i in ids]; ec_off=[B[i].get('eval_count') or 0 for i in ids]
    capbound=[i for i in ids if (A[i].get('eval_count') or 0)>=256 or (B[i].get('eval_count') or 0)>=256]
    chg_prompt_short=[i for i in shorter if A[i]['answer']!=B[i]['answer']]
    chg_prompt_eq=[i for i in eq if A[i]['answer']!=B[i]['answer']]
    print(f"{m}: n={n} called on/off {len(called)} | prompt tok mean on {np.mean([A[i]['prompt_tokens'] for i in called]):.1f} off {np.mean([B[i]['prompt_tokens'] for i in called]):.1f} max on {max(pt_on)} off {max(pt_off)} | context-cap bound (on prompt < off prompt): {len(shorter)}/{n} (mean reduction {np.mean([B[i]['prompt_tokens']-A[i]['prompt_tokens'] for i in shorter]) if shorter else 0:.0f} tok; max {max([B[i]['prompt_tokens']-A[i]['prompt_tokens'] for i in shorter] or [0])}); on>off {len(longer)}; equal {len(eq)}")
    print(f"    answers changed {len(changed)}/{n} (among prompt-shorter {len(chg_prompt_short)}/{len(shorter)}; among equal-prompt {len(chg_prompt_eq)}/{len(eq)}) | max answer tokens on {max(ec_on)} off {max(ec_off)}; items with eval_count>=256: on {sum(e>=256 for e in ec_on)} off {sum(e>=256 for e in ec_off)}; eval_count>256 off {sum(e>256 for e in ec_off)}| prompt token max (on cap 3200 chars~) | correct on {on['summary']['correct']} off {off['summary']['correct']}")
    # truncated answers: off answers exceeding 256 tokens that differ
    print('    mean total ms on/off',round(on['summary']['mean_total_ms']),round(off['summary']['mean_total_ms']),'tok/s',round(on['summary']['tokens_per_second'],1),round(off['summary']['tokens_per_second'],1), 'peak keys',[k for k in on['summary'] if 'peak' in k or 'vram' in k.lower() or 'ram' in k.lower()][:6])
