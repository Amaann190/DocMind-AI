# DocMind evaluation report

Generated 2026-11-17 22:41 · Mode: **live**
Chat model: not used · Embeddings: nomic-embed-text:latest

**17 passed · 0 failed · 0 skipped**

Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| retrieval | 17 | 0 | 0 |

## Retrieval ablation

11 answerable and 6 unanswerable queries · embeddings: nomic-embed-text:latest. Hit = an expected source is retrieved; rejection = nothing is retrieved for an unanswerable query. Latency excludes generation; configuration order is rotated per query.

| Configuration | Answerable hit rate | Correct rejection | Mean retrieval ms |
|---|---:|---:|---:|
| vector_only | 100% | 0% | 22.5 |
| bm25_only | 100% | 100% | 0.6 |
| hybrid_no_floor | 100% | 0% | 28.2 |
| full | 100% | 100% | 24.4 |

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

## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
