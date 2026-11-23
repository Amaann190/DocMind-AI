import json,csv,re,sys
sys.path.insert(0,'.')
from evaluation import squad
SP=r"paper/analysis/"
adj=list(csv.DictReader(open(SP+"squad_adjudication.csv",encoding="utf-8-sig")))
rel={x['id'] for x in adj if x['label'].startswith('answerable')}
PAT=[r"does(?: not|n't) (?:provide|mention|specify|contain|state|say|include|give|indicate|address)",
 r"\bdo(?:es)? not (?:explicitly )?(?:provide|mention|specify|contain)",
 r"\bno (?:specific |further |explicit |direct |relevant )?(?:information|mention|details?|data|reference|indication|evidence)\b",
 r"\bnot (?:explicitly )?(?:mentioned|specified|stated|available|given|provided|addressed|included|described|discussed|indicated|clear|listed|identified)",
 r"\bcannot (?:be )?(?:determine|determined|answer|answered|found|identify|identified|say|tell|conclude|infer|inferred)",
 r"\bcan(?:'|no)?t (?:be )?(?:determine|determined|answer|answered|find|identify|tell|say|conclude)",
 r"\bcould(?: not|n't) (?:find|determine|locate|identify|answer)",
 r"\bunable to (?:find|determine|locate|identify|answer|provide)",
 r"\bthere is no (?:mention|information|specific|explicit|indication|evidence|reference|data)",
 r"\b(?:is|are) not (?:mentioned|specified|stated|provided|given|available|addressed|explicitly)",
 r"\bnot (?:possible|able) to (?:determine|answer|say|find|identify)",
 r"\binsufficient (?:information|context|evidence)",
 r"\bi (?:don't|do not) (?:know|have)",
 r"\bnot enough information",
 r"\bno (?:such )?(?:answer|reference|record)\b",
 r"\bnot (?:addressed|covered) in",
 r"\bnone of the (?:sources|passages|documents|context)",
]
LEN=re.compile("|".join(PAT),re.I)
def lenient(a): return squad.is_refusal(a) or bool(LEN.search(a))
if __name__=='__main__':
    models=['qwen2.5-0.5b','qwen2.5-1.5b','qwen2.5-3b','qwen2.5-7b','llama3.2-1b','llama3.2-3b','llama3.1-8b','llama3-latest']
    print('patterns:',len(PAT))
    for m in models:
        d=json.load(open(f'paper/results/answers-{m}-full.json',encoding='utf8')); R=d['records']
        una=[r for r in R if r['unanswerable']]; ans=[r for r in R if not r['unanswerable']]
        una_c=[r for r in una if r['id'] not in rel]; ans_c=ans+[r for r in una if r['id'] in rel]
        S=lambda L:sum(squad.is_refusal(r['answer']) for r in L); Lc=lambda L:sum(lenient(r['answer']) for r in L)
        # sanity strict==refused flag
        assert all(bool(r['refused'])==squad.is_refusal(r['answer']) for r in R)
        diff=[r for r in R if lenient(r['answer'])!=squad.is_refusal(r['answer'])]
        qd=[r for r in ans if squad.contains_gold(r['answer'],r['answers']) and lenient(r['answer'])]
        qd_nostrict=[r for r in qd if not squad.is_refusal(r['answer'])]
        print(f"{m}: UNANS orig strict {S(una)}/100 lenient {Lc(una)}/100 | corrected strict {S(una_c)}/91 lenient {Lc(una_c)}/91 | ANS lenient-refusal orig {Lc(ans)}/100 (strict {S(ans)}) corrected {Lc(ans_c)}/109 (strict {S(ans_c)}) | diff items {len(diff)}/200 (una {sum(r['unanswerable'] for r in diff)}, ans {sum(not r['unanswerable'] for r in diff)}) | gold-contained & lenient-refusal {len(qd)} (of which strict-correct {len(qd_nostrict)}) | answerable strict-correct {sum(r['correct'] for r in ans)} -> lenient-adjusted {sum(r['correct'] and not lenient(r['answer']) for r in ans)}")
        diff=sorted(diff,key=lambda r:len(r['answer']))
        ex=[r for r in diff if r['unanswerable']][:1]+[r for r in diff if not r['unanswerable']][:1]
        if len(ex)<2: ex=diff[:2]
        for r in ex: print('   EX',('UNANS' if r['unanswerable'] else 'ANS'),repr(r['answer'][:150]),'| len',len(r['answer']),'| match:',(LEN.search(r['answer']) or [None])[0])
        for r in qd_nostrict[:1]: print('   QUOTE-DENY',repr(r['answer'][:200]))
