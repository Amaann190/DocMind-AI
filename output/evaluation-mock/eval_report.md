# DocMind evaluation report

Generated 2026-11-17 22:45 · Mode: **mock**
Chat model: not used · Embeddings: hash-mock

**47 passed · 0 failed · 34 skipped**
Live-answer checks separately: **0 passed · 0 failed · 34 skipped**


Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| ingestion | 7 | 0 | 0 |
| retrieval | 17 | 0 | 0 |
| generation | 5 | 0 | 34 |
| performance | 5 | 0 | 0 |
| robustness | 6 | 0 | 0 |
| architecture | 7 | 0 | 0 |

## Retrieval ablation

11 answerable and 6 unanswerable queries · embeddings: hash-mock. Hit = an expected source is retrieved; rejection = nothing is retrieved for an unanswerable query. Latency excludes generation; configuration order is rotated per query.

| Configuration | Answerable hit rate | Correct rejection | Mean retrieval ms |
|---|---:|---:|---:|
| vector_only | 82% | 50% | 0.6 |
| bm25_only | 100% | 100% | 0.4 |
| hybrid_no_floor | 100% | 50% | 1.1 |
| full | 100% | 100% | 1.1 |

## ingestion

- **PASSED — excluded_patterns**: loaded=1 patterns=34
- **PASSED — title_aware**: title='Annual Report'
- **PASSED — dedupe**: 4 -> 3 (distinct evidence preserved)
- **PASSED — multiformat_index**: loaded formats=['.csv', '.docx', '.md', '.txt']
- **PASSED — cache_key_and_persist**: key=bac3caf43182eeee2ac1 persist=hit
- **PASSED — min_chunk_filter**: MIN_CHARS=1 tiny_indexed=True
- **PASSED — helpers_github_normalize**: owner/repo=True url=True reject_gitlab=True

## retrieval

- **PASSED — What is the refund policy?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — money back rules**: vector_only: miss · bm25_only: hit · hybrid_no_floor: hit · full: hit
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
- **PASSED — what about purchases?**: vector_only: miss · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — Who painted the Mona Lisa?**: vector_only: miss · bm25_only: hit · hybrid_no_floor: miss · full: hit
- **PASSED — How do I repot an orchid?**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — Explain the plot of Hamlet**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit
- **PASSED — melting point of tungsten**: vector_only: hit · bm25_only: hit · hybrid_no_floor: hit · full: hit

## generation

- **PASSED — qa_template_guards**: has_guards=True len=1035
- **PASSED — query_helpers**: hyphen=True hinglish=True synonym=True
- **PASSED — no_hallucination_fallback**: fallback=hit
- **PASSED — tone_presets**: presets=6 distinct=True
- **PASSED — multi_turn_history**: messages_in_prompt=5
- **SKIPPED — refund_days**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — electronics_exception**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — exact_numbers**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — different_source_policies**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — conflicting_policies**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — unrelated_question**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — missing_detail**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — document_instruction_injection**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — follow_up**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.csv**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.doc**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.docx**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.eml**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.epub**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.htm**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.html**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.ipynb**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.json**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.jsonl**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.markdown**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.mbox**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.md**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.mhtml**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.msg**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.odt**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.pdf**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.ppt**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.pptx**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.rtf**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.tsv**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.txt**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.xls**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.xlsx**: Live answer check requires Ollama; --mock does not measure answer quality
- **SKIPPED — format.xml**: Live answer check requires Ollama; --mock does not measure answer quality

## performance

- **PASSED — ingest_5_docs**: 0.0s for 5 docs
- **PASSED — cache_hit_faster**: cold 0.0s vs cache 0.04s
- **PASSED — retrieval_latency**: vector 1ms hybrid 1ms
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
Ran 1 test in 6.466s

OK


## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
