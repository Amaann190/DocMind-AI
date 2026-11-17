# DocMind evaluation report

Generated 2026-11-17 22:40 · Mode: **live**
Chat model: not used · Embeddings: nomic-embed-text:latest

**2 passed · 0 failed · 0 skipped**

Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| benchmark | 2 | 0 | 0 |

## Retrieval benchmark

70 answerable, 32 off-topic and 12 near-miss queries over 20 documents · embeddings: nomic-embed-text:latest.
Recall@k counts distinct source files. Correct rejection = nothing retrieved for an off-topic query.
Near-miss retrieved is informational: retrieving the related document is acceptable there.

| Configuration | Recall@1 | Recall@3 | Recall@5 | MRR@5 | Correct rejection | Near-miss retrieved | ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| vector_only | 90% | 99% | 99% | 0.940 | 0% | 100% | 21.5 |
| bm25_only | 80% | 80% | 80% | 0.800 | 97% | 92% | 0.71 |
| hybrid_no_floor | 93% | 100% | 100% | 0.964 | 0% | 100% | 23.59 |
| full | 93% | 100% | 100% | 0.964 | 75% | 100% | 21.27 |

Recall@5 by query category:

| Category | Queries | vector_only | bm25_only | hybrid_no_floor | full |
|---|---:|---:|---:|---:|---:|
| hinglish | 6 | 100% | 33% | 100% | 100% |
| identifier | 11 | 91% | 100% | 100% | 100% |
| keyword | 26 | 100% | 96% | 100% | 100% |
| numeric | 4 | 100% | 100% | 100% | 100% |
| paraphrase | 23 | 100% | 61% | 100% | 100% |

## benchmark

- **PASSED — dataset_integrity**: 20 documents, 70 answerable, 32 off-topic, 12 near-miss
- **PASSED — benchmark_executed**: 114 queries x 4 configurations; metrics are in the summary

## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/eval-live
```
