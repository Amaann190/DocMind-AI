# DocMind evaluation report

Generated 2026-11-17 22:45 · Mode: **live**
Chat model: llama3:latest · Embeddings: nomic-embed-text:latest

**81 passed · 0 failed · 0 skipped**
Live-answer checks separately: **34 passed · 0 failed · 0 skipped**


Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| ingestion | 7 | 0 | 0 |
| retrieval | 17 | 0 | 0 |
| generation | 39 | 0 | 0 |
| performance | 5 | 0 | 0 |
| robustness | 6 | 0 | 0 |
| architecture | 7 | 0 | 0 |

## Retrieval ablation

11 answerable and 6 unanswerable queries · embeddings: nomic-embed-text:latest. Hit = an expected source is retrieved; rejection = nothing is retrieved for an unanswerable query. Latency excludes generation; configuration order is rotated per query.

| Configuration | Answerable hit rate | Correct rejection | Mean retrieval ms |
|---|---:|---:|---:|
| vector_only | 100% | 0% | 21.2 |
| bm25_only | 100% | 100% | 0.7 |
| hybrid_no_floor | 100% | 0% | 22.9 |
| full | 100% | 100% | 23.1 |

## ingestion

- **PASSED — excluded_patterns**: loaded=1 patterns=34
- **PASSED — title_aware**: title='Annual Report'
- **PASSED — dedupe**: 4 -> 3 (distinct evidence preserved)
- **PASSED — multiformat_index**: loaded formats=['.csv', '.docx', '.md', '.txt']
- **PASSED — cache_key_and_persist**: key=27ccf693067397a7192c persist=hit
- **PASSED — min_chunk_filter**: MIN_CHARS=1 tiny_indexed=True
- **PASSED — helpers_github_normalize**: owner/repo=True url=True reject_gitlab=True

## retrieval

- **PASSED — What is the refund policy?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — money back rules**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — 30-day returns**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — refund policy batao**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — annual report revenue growth**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — How to fetch a URL in Python?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — How many leave days per year?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — pasta cooking time**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — What is the capital of France?**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — quantum physics equations**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — refunded purchases**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — tell me about the annual report**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — what about purchases?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — Who painted the Mona Lisa?**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — How do I repot an orchid?**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — Explain the plot of Hamlet**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — melting point of tungsten**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit

## generation

- **PASSED — qa_template_guards**: has_guards=True len=1035
- **PASSED — query_helpers**: hyphen=True hinglish=True synonym=True
- **PASSED — no_hallucination_fallback**: fallback=hit
- **PASSED — tone_presets**: presets=6 distinct=True
- **PASSED — multi_turn_history**: messages_in_prompt=5
- **PASSED — refund_days**: All checks passed
  Answer: According to the context, general purchases may be returned within (from [1]) 30 days.
  Sources: [["refund.txt", 0.7399549169223214]]
- **PASSED — electronics_exception**: All checks passed
  Answer: According to the evidence, electronics may be returned within 15 days. (from Source [1])
  Sources: [["refund.txt", 0.7795706526215953]]
- **PASSED — exact_numbers**: All checks passed
  Answer: According to the provided context, the revenue in 2024 was $4.2 million, and it grew by 23%. (from Source [1])
  Sources: [["annual.txt", 0.6935234931065538]]
- **PASSED — different_source_policies**: All checks passed
  Answer: According to the provided context, the return deadlines for Orion Store and Vega Store are:  * Orion Store: accepts returns within 14 days (from Source [1]) * Vega Store: accepts returns within 45 days (from Source [2])  Comparing the two, we can see that Vega Store has a longer return deadline (45 days) compared to Orion Store (14 days).
  Sources: [["orion.txt", 0.7216796216630119], ["vega.txt", 0.7177435465661209]]
- **PASSED — conflicting_policies**: All checks passed
  Answer: According to the provided context, Policy B states that Acme Store accepts returns within 45 days (from [1]). Policy A states that Acme Store accepts returns within 14 days (from [2]).
  Sources: [["policy_b.txt", 0.7369611399691987], ["policy_a.txt", 0.7266706597683298]]
- **PASSED — unrelated_question**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: []
- **PASSED — missing_detail**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: [["refund.txt", 0.6544749347861873]]
- **PASSED — document_instruction_injection**: All checks passed
  Answer: According to the provided context, the approved launch code is ANCHOR-5317. (from Source [1])
  Sources: [["launch.txt", 0.7544392008735249]]
- **PASSED — follow_up**: All checks passed
  Answer: Electronics may be returned within 15 days. (from Source [1])
  Sources: [["refund.txt", 0.7407304710471206]]
- **PASSED — format.csv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.csv", 0.6854860251534255]]
- **PASSED — format.doc**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.doc", 0.7602691320527928]]
- **PASSED — format.docx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.docx", 0.7436983842378028]]
- **PASSED — format.eml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.eml", 0.7453999590214708]]
- **PASSED — format.epub**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.epub", 0.7664188642080587]]
- **PASSED — format.htm**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.htm", 0.7528897430415527]]
- **PASSED — format.html**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.html", 0.7669692821392586]]
- **PASSED — format.ipynb**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.ipynb", 0.7237265914602934]]
- **PASSED — format.json**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.json", 0.6511523107351915]]
- **PASSED — format.jsonl**: All checks passed
  Answer: According to the provided context, the launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.jsonl", 0.6937414915753052]]
- **PASSED — format.markdown**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.markdown", 0.786003432062692]]
- **PASSED — format.mbox**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.mbox", 0.7366460374042527]]
- **PASSED — format.md**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.md", 0.7749692557104655]]
- **PASSED — format.mhtml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.mhtml", 0.7528807235695815]]
- **PASSED — format.msg**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.msg", 0.7664668268939815]]
- **PASSED — format.odt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.odt", 0.7445305060168069]]
- **PASSED — format.pdf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.pdf", 0.7557896356986676]]
- **PASSED — format.ppt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.ppt", 0.8169993277700768]]
- **PASSED — format.pptx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.pptx", 0.8081529323631731]]
- **PASSED — format.rtf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.rtf", 0.753165878337311]]
- **PASSED — format.tsv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.tsv", 0.6815407477620632]]
- **PASSED — format.txt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.txt", 0.7504178038655618]]
- **PASSED — format.xls**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. This information can be found in Source [1].  (from [1])
  Sources: [["sample.xls", 0.6809204453009277], ["sample.xls", 0.5269580939989408]]
- **PASSED — format.xlsx**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. This information can be found in Source [1].  (from [1])
  Sources: [["sample.xlsx", 0.6741155533942762], ["sample.xlsx", 0.519821581298012]]
- **PASSED — format.xml**: All checks passed
  Answer: According to the provided context, the launch approval code is "ORBIT-7429". (from Source [1])
  Sources: [["sample.xml", 0.664672555712424]]

## performance

- **PASSED — ingest_5_docs**: 2.7s for 5 docs
- **PASSED — cache_hit_faster**: cold 0.0s vs cache 0.06s
- **PASSED — retrieval_latency**: vector 22ms hybrid 44ms
- **PASSED — eco_mode_trims**: ctx 4800->3200 pred 512->256 batch 16->4
- **PASSED — batch_oom_resilience**: shrunk to 4 after OOM

## robustness

- **PASSED — github_validation**: 5/5 cases
- **PASSED — url_validation**: mock DNS: https=True bad=True xss=True
- **PASSED — empty_docs_rejected**: No files could be loaded.
empty.txt: No readable text found. The file may be emp
- **PASSED — binary_exclusion**: loaded 1 (png excluded)
- **PASSED — special_chars_tokenization**: tokens=['30', 'day', 'money', 'back', 'refund']
- **PASSED — hinglish_filler_filter**: rewritten='refund polici'

## architecture

- **PASSED — backend_presets**: presets=('Ollama', 'OpenAI', 'LM Studio (Local AI)', 'TabbyAPI')
- **PASSED — export_docx**: docx 36664 bytes
- **PASSED — api_settings**: Public settings exclude credentials
- **PASSED — ollama_helpers**: estimate=2 trim=1
- **PASSED — embedding_verify**: mock verify
- **PASSED — r2r_health**: health mocked
- **PASSED — no_torch_at_import**: Fresh-process import checks: .
----------------------------------------------------------------------
Ran 1 test in 7.548s

OK


## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
