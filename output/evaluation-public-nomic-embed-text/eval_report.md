# DocMind evaluation report

Generated 2026-11-17 22:17 · Mode: **live**
Chat model: not used · Embeddings: nomic-embed-text:latest

**2 passed · 0 failed · 0 skipped**

Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| public | 2 | 0 | 0 |

## Public benchmark: BEIR SciFact

300 test claims over 5183 abstracts · embeddings: nomic-embed-text:latest · indexing took 170.7 s. No result = share of claims for which the configuration returned nothing.

| Configuration | nDCG@10 | Recall@1 | Recall@5 | Recall@10 | MRR@10 | No result |
|---|---:|---:|---:|---:|---:|---:|
| vector_only | 0.707 | 60% | 78% | 83% | 0.679 | 0% |
| bm25_only | 0.543 | 49% | 59% | 61% | 0.535 | 12% |
| hybrid_no_floor | 0.718 | 60% | 82% | 86% | 0.688 | 0% |
| full | 0.718 | 60% | 82% | 86% | 0.688 | 0% |

## public

- **PASSED — dataset**: 5183 abstracts, 300 test claims
- **PASSED — public_benchmark_executed**: 300 claims x 4 configurations; metrics are in the summary

## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
