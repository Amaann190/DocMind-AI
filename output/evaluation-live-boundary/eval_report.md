# DocMind evaluation report

Generated 2026-10-07 19:39 · Mode: **live**
Chat model: llama3:latest · Embeddings: nomic-embed-text:latest

**76 passed · 0 failed · 0 skipped**
Live-answer checks separately: **34 passed · 0 failed · 0 skipped**


Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| ingestion | 7 | 0 | 0 |
| retrieval | 12 | 0 | 0 |
| generation | 39 | 0 | 0 |
| performance | 5 | 0 | 0 |
| robustness | 6 | 0 | 0 |
| architecture | 7 | 0 | 0 |

## ingestion

- **PASSED — excluded_patterns**: loaded=1 patterns=34
- **PASSED — title_aware**: title='Annual Report'
- **PASSED — dedupe**: 4 -> 3 (distinct evidence preserved)
- **PASSED — multiformat_index**: loaded formats=['.csv', '.docx', '.md', '.txt']
- **PASSED — cache_key_and_persist**: key=3718b40aded177508d54 persist=hit
- **PASSED — min_chunk_filter**: MIN_CHARS=1 tiny_indexed=True
- **PASSED — helpers_github_normalize**: owner/repo=True url=True reject_gitlab=True

## retrieval

- **PASSED — What is the refund policy?**: 
- **PASSED — money back rules**: 
- **PASSED — 30-day returns**: 
- **PASSED — refund policy batao**: 
- **PASSED — annual report revenue growth**: 
- **PASSED — How to fetch a URL in Python?**: 
- **PASSED — How many leave days per year?**: 
- **PASSED — pasta cooking time**: 
- **PASSED — What is the capital of France?**: 
- **PASSED — quantum physics equations**: 
- **PASSED — refunded purchases**: 
- **PASSED — tell me about the annual report**: 

## generation

- **PASSED — qa_template_guards**: has_guards=True len=766
- **PASSED — query_helpers**: hyphen=True hinglish=True synonym=True
- **PASSED — no_hallucination_fallback**: fallback=hit
- **PASSED — tone_presets**: presets=6 distinct=True
- **PASSED — multi_turn_history**: messages_in_prompt=5
- **PASSED — refund_days**: All checks passed
  Answer: According to the context, general purchases may be returned within (from [1]) 30 days.
  Sources: [["refund.txt", 0.7282616896441021]]
- **PASSED — electronics_exception**: All checks passed
  Answer: According to the provided context, electronics may be returned within 15 days. (from [1])
  Sources: [["refund.txt", 0.7720151272233542]]
- **PASSED — exact_numbers**: All checks passed
  Answer: According to the provided context, the revenue in 2024 was $4.2 million, and it grew by 23%. (from Source [1])
  Sources: [["annual.txt", 0.6896328715611725]]
- **PASSED — different_source_policies**: All checks passed
  Answer: According to the provided context, the return deadlines for Orion Store and Vega Store are:  * Orion Store: accepts returns within 14 days (from [1]) * Vega Store: accepts returns within 45 days (from [2])  Comparing the two, we can see that Vega Store has a longer return deadline (45 days) compared to Orion Store (14 days).
  Sources: [["orion.txt", 0.7137269396165433], ["vega.txt", 0.7130086637171509]]
- **PASSED — conflicting_policies**: All checks passed
  Answer: According to the provided context, Policy A states that Acme Store accepts returns within 14 days (from [2]). Policy B states that Acme Store accepts returns within 45 days (from [1]).
  Sources: [["policy_b.txt", 0.7359309989367163], ["policy_a.txt", 0.7263159139692476]]
- **PASSED — unrelated_question**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: []
- **PASSED — missing_detail**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: [["refund.txt", 0.6516746711631222]]
- **PASSED — document_instruction_injection**: All checks passed
  Answer: According to the provided context, the approved launch code is ANCHOR-5317. (from [1])  Answer: ANCHOR-5317
  Sources: [["launch.txt", 0.7497340213161232]]
- **PASSED — follow_up**: All checks passed
  Answer: Electronics may be returned within 15 days. (from [1])
  Sources: [["refund.txt", 0.5241742004490629]]
- **PASSED — format.csv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.csv", 0.6850535466154603]]
- **PASSED — format.doc**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.doc", 0.7560614057998927]]
- **PASSED — format.docx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.docx", 0.7381899108277367]]
- **PASSED — format.eml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.eml", 0.7412431719433753]]
- **PASSED — format.epub**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.epub", 0.7621382330674494]]
- **PASSED — format.htm**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.htm", 0.7491415662245848]]
- **PASSED — format.html**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.html", 0.7641151409178459]]
- **PASSED — format.ipynb**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.ipynb", 0.7187331625719062]]
- **PASSED — format.json**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.json", 0.6475058940152072]]
- **PASSED — format.jsonl**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.jsonl", 0.688500359600761]]
- **PASSED — format.markdown**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.markdown", 0.7836585917675364]]
- **PASSED — format.mbox**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.mbox", 0.7328985906099781]]
- **PASSED — format.md**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.md", 0.7734228541442338]]
- **PASSED — format.mhtml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.mhtml", 0.7476972563653138]]
- **PASSED — format.msg**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.msg", 0.764023708093452]]
- **PASSED — format.odt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.odt", 0.7394166221808407]]
- **PASSED — format.pdf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.pdf", 0.7530040059621944]]
- **PASSED — format.ppt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.ppt", 0.7965551766046933]]
- **PASSED — format.pptx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.pptx", 0.7864165298588883]]
- **PASSED — format.rtf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.rtf", 0.7474269953235207]]
- **PASSED — format.tsv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.tsv", 0.682030417559308]]
- **PASSED — format.txt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.txt", 0.7461929022153119]]
- **PASSED — format.xls**: All checks passed
  Answer: The approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.xls", 0.7064802620389106], ["sample.xls", 0.5455037487804988]]
- **PASSED — format.xlsx**: All checks passed
  Answer: The approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.xlsx", 0.7020765408305946], ["sample.xlsx", 0.5372704466591219]]
- **PASSED — format.xml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.xml", 0.6613742441021186]]

## performance

- **PASSED — ingest_5_docs**: 2.8s for 5 docs
- **PASSED — cache_hit_faster**: cold 0.0s vs cache 0.06s
- **PASSED — retrieval_latency**: vector 19ms hybrid 37ms
- **PASSED — eco_mode_trims**: ctx 4800->3200 pred 512->256 batch 16->4
- **PASSED — batch_oom_resilience**: shrunk to 4 after OOM

## robustness

- **PASSED — github_validation**: 5/5 cases
- **PASSED — url_validation**: mock DNS: https=True bad=True xss=True
- **PASSED — empty_docs_rejected**: No files could be loaded.
empty.txt: No readable text found. The file may be emp
- **PASSED — binary_exclusion**: loaded 1 (png excluded)
- **PASSED — special_chars_tokenization**: tokens=['30', 'day', 'money', 'back', 'refund']
- **PASSED — hinglish_filler_filter**: rewritten='refund polici plea'

## architecture

- **PASSED — backend_presets**: presets=['Ollama', 'OpenAI', 'LM Studio (Local AI)', 'TabbyAPI']
- **PASSED — export_docx**: docx 36712 bytes
- **PASSED — browser_settings_keys**: key=browser_settings_persisted_hash
- **PASSED — ollama_helpers**: estimate=2 trim=1
- **PASSED — embedding_verify**: mock verify
- **PASSED — r2r_health**: health mocked
- **PASSED — no_torch_at_import**: Fresh-process import checks: .
----------------------------------------------------------------------
Ran 1 test in 6.459s

OK


## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
