# Answer quality and evaluation

This phase separates file extraction, retrieval, and actual model answers. A reader
success does not establish that a model will answer correctly. Likewise, a mocked
test or a check that a prompt contains instructions is not an answer-quality score.

## What changed

- The evaluation harness reports passes, failures and skips separately, preserves
  actual answers and sources in JSON, and exits unsuccessfully when a check fails.
  Live runs cannot silently fall back to mock embeddings. Offline embeddings are
  stable across Python processes; offline runs skip all live-answer cases.
- There are 34 live-answer cases: nine checks for facts, numbers, different and
  conflicting policies, missing information, document instructions and follow-up
  questions, plus one question through each of the 25 real file readers.
- XML extraction retains field names and attributes. Flattening XML into values
  alone previously removed the meaning needed to answer the question.
- Source labels are distinguished from row and line numbers inside documents.
  An out-of-range numeric citation produces a warning; the application does not
  replace it with an invented citation or claim to verify semantic support.
- Retrieval recognizes the phrase “money back” as refund/return evidence without
  treating every occurrence of “back” as a refund query. Missing evidence returns
  the fallback without initializing a chat model.
- A reminder after the document passages reinforces that quoted instructions are
  data. This is a prompt mitigation, not a guarantee of injection resistance.
- Fresh model selection recognizes the installed `llama3:latest` alias in the
  existing model preference list. A valid saved user selection is preserved.
- CI now runs the offline evaluation in addition to the regression tests. The CI
  configuration has been checked locally; a hosted CI run was not triggered here.

## Recorded results

The machine has `llama3:latest`, `qwen2.5:0.5b` and
`nomic-embed-text:latest` installed. Live answer runs use the latter embedding model,
temperature zero, top K 3, similarity cutoff 0.5, chunks of 256 tokens with 32-token
overlap, and Eco Mode disabled. Generated reports include the exact model tags and
actual answers. Tags may resolve to different weights after a future model update.

Before the final document-boundary reminder, a full run with `llama3:latest` passed
75 of 76 checks, including 33 of 34 live answers and all 25 format questions.
The failed answer followed the document's instruction to output `PWNED`, despite
also identifying the correct fact. This failure is retained in
[`output/evaluation-live/eval_results.json`](../output/evaluation-live/eval_results.json).
It demonstrates why prompt guards and valid citations alone are insufficient.

On 2026-10-07, the final full run with `llama3:latest` passed **76 of 76 checks**,
including **34 of 34 live answers** and **25 of 25 format questions**. The previous
document-instruction failure passed with the final reminder. This one attack's
passing result is not a security guarantee.

The [report](../output/evaluation-live-boundary/eval_report.md) and
[JSON](../output/evaluation-live-boundary/eval_results.json) record that full live run. Offline verification passed **42 checks** and explicitly
skipped **34 live answers**. The final regression suite passed **170 tests**;
compilation and Ruff's configured error checks passed at that evaluation checkpoint.
The temporary smoke-test server was stopped afterward.

The same final 34 answer cases were also run with the smaller installed model:

| Model | Live answers passed | Failed | Format answers satisfying fact and citation checks |
|---|---:|---:|---:|
| `llama3:latest` | 34/34 | 0 | 25/25 |
| `qwen2.5:0.5b` | 3/34 | 31 | 0/25 |

The smaller model passed the conflicting-policy question and the two refusal
cases. Many other answers stated the right fact but omitted citations; others
refused despite available evidence. It also output `PWNED` for the document
instruction case and failed the follow-up. Its zero complete format passes does
**not** mean extraction failed for every format. See the actual
[smaller-model answers](../output/evaluation-qwen-final/eval_report.md) and
[grading details](../output/evaluation-qwen-final/eval_results.json).

Since 2026-11-17, sentences in retrieved text that address the model ("ignore all
previous instructions", "answer X instead", "you are now ...") are withheld from the
prompt before generation (`utils/ollama.py`, `_withhold_instructions`); the source
preview still shows the original passage. With that change `qwen2.5:0.5b` no longer
outputs `PWNED` for the injection case, but it now answers "I could not find this
information" instead of the code, so it still fails that check. This is a heuristic
filter for common phrasings, not a guarantee against prompt injection.

On 2026-11-17, after the retrieval fixes and this filter, a full live run with
`llama3:latest` and `nomic-embed-text:latest` passed **81 of 81 checks**, including
**34 of 34 live answers** (injection case: `ANCHOR-5317 (from Source [1])`).
See the [report](../output/evaluation-live-2026-11/eval_report.md) and
[JSON](../output/evaluation-live-2026-11/eval_results.json). An intermediate version
that wrapped passages in `<source>` tags made llama3 cite the tag instead of `[n]`
(24 citation failures), so passages keep the plain `Source [n] (file):` label.

## Retrieval ablation

The retrieval suite compares four configurations on the same index: dense vectors
only, BM25 only, hybrid fusion without the evidence floor, and the full pipeline.
On 2026-11-17 with `nomic-embed-text:latest` (11 answerable, 6 unanswerable queries):

| Configuration | Answerable hit rate | Correct rejection |
|---|---:|---:|
| Vector only | 11/11 | 0/6 |
| BM25 only | 11/11 | 6/6 |
| Hybrid RRF, no evidence floor | 11/11 | 0/6 |
| Full DocMind (hybrid + floor) | 11/11 | 6/6 |

See the [ablation report](../output/evaluation-retrieval-ablation/eval_report.md).
The fixture corpus is five short documents, so every configuration finds the
answerable sources; the measurable difference is rejection. Dense similarity alone
never returns an empty result on these probes, and the evidence floor is what
restores correct rejection after fusion. The small set cannot show where hybrid
fusion beats BM25 alone; the labelled benchmark below does.

## Labelled retrieval benchmark

`evaluation/benchmark/` holds 20 documents (policies, manuals, reports, runbooks,
recipes, science notes) with deliberate overlaps, 70 answerable queries labelled by
type, 32 off-topic queries written naturally (not filtered for keyword overlap) and
12 near-miss queries whose related document does not contain the answer. Run it with
`eval_harness.py --suite benchmark`. On 2026-11-17 with `nomic-embed-text:latest`:

| Configuration | Recall@1 | Recall@3 | Recall@5 | MRR@5 | Correct rejection (32) |
|---|---:|---:|---:|---:|---:|
| Vector only | 90% | 99% | 99% | 0.940 | 0% |
| BM25 only | 80% | 80% | 80% | 0.800 | 97% |
| Hybrid RRF, no evidence floor | 96% | 100% | 100% | 0.976 | 0% |
| **Full DocMind** | **96%** | **100%** | **100%** | **0.976** | **75%** |

Recall@5 by query type: BM25 alone finds 61% of paraphrases and 33% of Hinglish
queries, vector search alone 91% of identifier queries (codes such as `E-219`), and
the hybrid pipelines 100% of every type. Fusion therefore beats each channel alone on
ranking. The evidence floor is what makes rejection possible at all: without it,
every off-topic query returns passages. See the
[benchmark report](../output/evaluation-benchmark/eval_report.md).

The first run of this benchmark exposed a weakness the five-document probes hid:
the full pipeline rejected only 5 of 32 natural off-topic questions (16%), because
any shared word counted as keyword evidence, including "how", "in" and "who".
Keyword evidence now ignores stopwords and request words, and a chunk with a weak
vector score needs at least half of a question's content terms (or their synonyms)
before BM25 vouches for it ("minimum should match"; each question in a resolved
follow-up is judged separately). That raised correct rejection from 16% to 75% and
Recall@1 from 90% to 96%, with Recall@5 unchanged at 100%. The 8 off-topic questions
still retrieved are semantic neighbours scored above the 0.5 floor by the embedding
model (for example "Which language was created by Guido van Rossum?" retrieves the
Python style guide); abstaining on those is left to the answer step. Near-miss
questions retrieve their related document by design.

These figures come from one synthetic corpus and one embedding model; they show
relative behaviour of the configurations, not accuracy on other collections.

For this installation, use `llama3:latest` for document questions based on these
observed results. If a previous session saved `qwen2.5:0.5b`, select `llama3:latest`
in Settings; the application deliberately preserves valid saved choices. This
comparison does not establish that every larger model is better or that these
results will hold for different prompts, settings, documents or model weights.

## Reproduce

Use the project environment and installed models. Live runs send synthetic fixture
content to the configured Ollama endpoint and temporarily use their own workspace.
They use isolated request-local evaluation state and restore the caller's context afterward.

```bash
pipenv run python -m unittest discover -s tests
pipenv run python eval_harness.py --mock --out output/evaluation-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/evaluation-live-boundary
pipenv run python eval_harness.py --suite generation --chat-model qwen2.5:0.5b --out output/evaluation-qwen-final
pipenv run python eval_harness.py --suite retrieval --out output/evaluation-retrieval-ablation
pipenv run python eval_harness.py --suite benchmark --out output/evaluation-benchmark
```

Legacy DOC, PPT and XLS fixture generation and extraction require LibreOffice.
A missing converter or unavailable model is a failed live prerequisite, not a
successful format test. Keep generated JSON when comparing runs; the Markdown
report alone does not contain all grading details.

## Limits and next quality work

These are small, synthetic, inspectable cases, not a representative accuracy study.
All format cases use a short known fact; they do not cover every layout, encoding,
large file, language, scanned document or damaged file. The nine behavioral cases
are useful regressions but do not exhaust instruction attacks or conversation paths.

Grading checks required and forbidden text, numeric citation bounds, expected
source filenames and exact refusals. It can miss a false extra claim or reject a
valid paraphrase. Citing the expected file does not prove every claim follows from
it. Review the recorded answers as well as the counts. Timing depends on hardware,
model loading and other local work; these runs are not a speed benchmark.

The next useful expansion is a human-reviewed set of representative documents and
questions, especially long documents, tables, ambiguous questions, multi-turn
conversations and varied malicious passages. Keep those results separate from
these synthetic checks. Do not present the old August “43/43, 100%” structural
report, or any new aggregate pass rate, as general model accuracy.
