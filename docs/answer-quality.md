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

The repository-root [report](../eval_report.md) and [JSON](../eval_results.json)
record that full live run. Offline verification passed **42 checks** and explicitly
skipped **34 live answers**. The final regression suite passed **170 tests**;
compilation, Ruff's configured error checks and a Streamlit health check passed.
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

For this installation, use `llama3:latest` for document questions based on these
observed results. If a previous session saved `qwen2.5:0.5b`, select `llama3:latest`
in Settings; the application deliberately preserves valid saved choices. This
comparison does not establish that every larger model is better or that these
results will hold for different prompts, settings, documents or model weights.

## Reproduce

Use the project environment and installed models. Live runs send synthetic fixture
content to the configured Ollama endpoint and temporarily use their own workspace.
They restore the evaluator's Streamlit state afterward.

```bash
pipenv run python -m unittest discover -s tests
pipenv run python eval_harness.py --mock --out output/evaluation-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/evaluation-live-boundary
pipenv run python eval_harness.py --suite generation --chat-model qwen2.5:0.5b --out output/evaluation-qwen-final
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
