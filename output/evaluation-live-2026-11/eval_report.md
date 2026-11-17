# DocMind evaluation report

Generated 2026-11-17 20:29 · Mode: **live**
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
| vector_only | 100% | 0% | 38.9 |
| bm25_only | 100% | 100% | 1.1 |
| hybrid_no_floor | 100% | 0% | 43.4 |
| full | 100% | 100% | 37.4 |

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
  Answer: According to the evidence, general purchases may be returned within (from [1]) 30 days.
  Sources: [["refund.txt", 0.7342138214267222]]
- **PASSED — electronics_exception**: All checks passed
  Answer: According to the evidence, electronics may be returned within 15 days. (from Source [1])
  Sources: [["refund.txt", 0.7773064758636228]]
- **PASSED — exact_numbers**: All checks passed
  Answer: According to the provided context, the revenue in 2024 was $4.2 million, and it grew by 23%. (from Source [1])
  Sources: [["annual.txt", 0.6922727708957754]]
- **PASSED — different_source_policies**: All checks passed
  Answer: According to the provided context, the return deadlines for Orion Store and Vega Store are:  * Orion Store: accepts returns within 14 days (from Source [1]) * Vega Store: accepts returns within 45 days (from Source [2])  Comparing the two, we can see that Vega Store has a longer return deadline (45 days) compared to Orion Store (14 days).
  Sources: [["orion.txt", 0.7234364520289789], ["vega.txt", 0.7172202409352225]]
- **PASSED — conflicting_policies**: All checks passed
  Answer: According to the provided context, Policy B states that Acme Store accepts returns within 45 days (from [1]). Policy A states that Acme Store accepts returns within 14 days (from [2]).
  Sources: [["policy_b.txt", 0.7361684520948779], ["policy_a.txt", 0.7275255909392722]]
- **PASSED — unrelated_question**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: []
- **PASSED — missing_detail**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: [["refund.txt", 0.647401044039096]]
- **PASSED — document_instruction_injection**: All checks passed
  Answer: According to the provided context, the approved launch code is ANCHOR-5317. (from Source [1])
  Sources: [["launch.txt", 0.7598925956095346]]
- **PASSED — follow_up**: All checks passed
  Answer: Electronics may be returned within 15 days. (from Source [1])
  Sources: [["refund.txt", 0.7382543065979548]]
- **PASSED — format.csv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.csv", 0.6807609180483883]]
- **PASSED — format.doc**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.doc", 0.7596230280969878]]
- **PASSED — format.docx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.docx", 0.7445837888567942]]
- **PASSED — format.eml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.eml", 0.7450193450916184]]
- **PASSED — format.epub**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.epub", 0.7647995016995182]]
- **PASSED — format.htm**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.htm", 0.753655902409233]]
- **PASSED — format.html**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.html", 0.7677087229071367]]
- **PASSED — format.ipynb**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.ipynb", 0.7237548414530723]]
- **PASSED — format.json**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.json", 0.6569833018150455]]
- **PASSED — format.jsonl**: All checks passed
  Answer: According to the provided context, the launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.jsonl", 0.695687669860445]]
- **PASSED — format.markdown**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.markdown", 0.7897195494747955]]
- **PASSED — format.mbox**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.mbox", 0.7379750906505625]]
- **PASSED — format.md**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.md", 0.7764892778497433]]
- **PASSED — format.mhtml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.mhtml", 0.7520841767357009]]
- **PASSED — format.msg**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.msg", 0.7678630997649533]]
- **PASSED — format.odt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.odt", 0.7444366610645772]]
- **PASSED — format.pdf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.pdf", 0.7553238316815618]]
- **PASSED — format.ppt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.ppt", 0.8169993277700768]]
- **PASSED — format.pptx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (Source [1])
  Sources: [["sample.pptx", 0.8081529323631731]]
- **PASSED — format.rtf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.rtf", 0.7516161023621364]]
- **PASSED — format.tsv**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.tsv", 0.6780073469156209]]
- **PASSED — format.txt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from Source [1])
  Sources: [["sample.txt", 0.751353649023696]]
- **PASSED — format.xls**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. This information can be found in Source [1].  (from [1])
  Sources: [["sample.xls", 0.6726582879947729], ["sample.xls", 0.5199105754801335]]
- **PASSED — format.xlsx**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. This information can be found in Source [1]. (from [1])
  Sources: [["sample.xlsx", 0.6656285667014435], ["sample.xlsx", 0.5116500068561185]]
- **PASSED — format.xml**: All checks passed
  Answer: According to the provided context, the launch approval code is "ORBIT-7429". (from Source [1])
  Sources: [["sample.xml", 0.6625961143556883]]

## performance

- **PASSED — ingest_5_docs**: 3.0s for 5 docs
- **PASSED — cache_hit_faster**: cold 0.0s vs cache 0.08s
- **PASSED — retrieval_latency**: vector 29ms hybrid 36ms
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
Ran 1 test in 11.406s

OK


## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
