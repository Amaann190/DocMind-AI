# Completed repairs and verification

Updated 2026-10-08. This records the work across the original repair sequence,
including the final user-experience/failure-recovery and documentation/release
checkpoints. Those checkpoints have been implemented; verification limits are
listed below rather than converted into new required phases.

## Original scope

1. Make every supported format extract text.
2. Preserve information and report ingestion failures.
3. Repair retrieval and application behavior.
4. Harden and verify installation/deployment.

The original advertised count of 26 was incorrect: the application has 25 supported
extensions. Extraction support does not mean every arbitrary file or model answer
will work. Scanned images, email attachments and damaged/encrypted files are outside
the verified extraction scope described in [usage](usage.md).

## What was added and repaired, from the start

### Document support and ingestion

- Configured readers and dependencies for all 25 extensions: CSV, DOC, DOCX, EML,
  EPUB, HTM, HTML, IPYNB, JSON, JSONL, Markdown, MBOX, MD, MHTML, MSG, ODT, PDF,
  PPT, PPTX, RTF, TSV, TXT, XLS, XLSX and XML. LibreOffice provides legacy Office
  conversion. Uploads and repository ingestion share the reader configuration.
- Added real synthetic fixtures for every extension, covering extraction rather
  than only checking extension names. All 25 passed on Windows and in the earlier
  Linux container validation.
- Fixed CSV header/double-parsing problems, incomplete JSON/JSONL extraction and
  loss of XML field/attribute meaning. Preserved short facts and codes.
- Limited deduplication to exact duplicates at the same source/location; retained
  distinct values, negations and source identities, without merging unrelated files.
- Added per-file diagnostics and partial-success reporting. Empty or invalid input
  does not silently become a successful searchable collection.

### Retrieval, answers and evaluation

- Repaired hybrid keyword/vector retrieval so useful keyword matches can rescue
  missed vector results; unrelated keyword candidates do not enter fusion.
- Restricted topic-specific summaries to relevant evidence. Budgeted the full
  prompt, history and answer, with explicit models and chunk settings.
- Removed fabricated fallback citations. Numbered sources remain tied to retrieved
  passages; out-of-range citations produce a warning rather than invented support.
- Added a document-instruction reminder and missing-evidence fallback. Prompt
  mitigation and numeric citation validation do not prove an answer is safe or true.
- Added 34 live-answer cases (nine behavioral cases and 25 format questions), stable
  mock embeddings, explicit pass/fail/skip results and saved actual answers. Live
  failures cannot silently become mock successes. CI includes offline evaluation.
- Recognized the installed `llama3:latest` alias in default model preference while
  preserving valid saved selections. The recorded comparison supports using that
  installed model for document questions; see [answer-quality results](answer-quality.md).

### Isolation and input safety

- Replaced shared application model/workspace state with session-owned models,
  temporary directories and index caches. Cache identity includes provider,
  endpoint, source metadata and ingestion settings; cleanup is session-scoped.
- Tightened upload names, resolved paths, sizes and archive limits; isolated GitHub
  clones and validated both accepted repository input forms.
- Enforced public HTTPS website destinations, checked redirects, response limits
  and TLS, and pinned connections to validated IPs to reduce DNS-rebinding exposure.
- Kept credentials out of browser preference storage. See [security boundaries](security.md).

### User experience and failure recovery — final checkpoint

- Kept Settings usable after ingestion errors. Failed uploads no longer retry on
  every unrelated rerun; **Reprocess files** provides an explicit retry and applies
  changed embedding/chunk settings.
- Fixed the disappearing **Ask without documents** action so it survives reruns
  and actually performs direct chat.
- Preserved partial streamed answers with an interruption message; a subsequent
  question can still work.
- Retained numbered sources with each saved assistant message and included them
  in Word exports, without presenting retrieval scores as confidence percentages.
- Replaced free-text chunk size with a bounded numeric control. Validated restored
  numeric values, provider/style choices and chunk overlap; persisted answer style.
  Browser storage failures no longer leave initialization waiting indefinitely.
- Corrected OpenAI, LM Studio and TabbyAPI routing for chat and embeddings. Local
  model names use compatible chat metadata without requiring an OpenAI model-name
  registry entry. Temperature changes apply to newly created clients.
- Repaired Clear Chat/reset state, source inputs, credentials, model discovery and
  uploader replacement. Reset keeps failed remote cleanup information for retry.
- Corrected R2R health/upload/query contracts, scoped queries to owned document IDs,
  tracked unique IDs before upload, retained original server credentials for cleanup,
  and blocked stale-server queries. R2R does not require a local Ollama model or
  silently fall back to local retrieval. GitHub/Website imports clearly explain that
  R2R mode supports Local Files only.
- Added 14 workflow tests using real Streamlit reruns with controlled external
  services, including actual reader ingestion, partial failures and compatible SDK
  streaming. These complement, rather than replace, browser verification.

R2R request shapes were checked against the upstream SDK's
[documents](https://github.com/SciPhi-AI/R2R/blob/main/py/sdk/sync_methods/documents.py),
[retrieval](https://github.com/SciPhi-AI/R2R/blob/main/py/sdk/sync_methods/retrieval.py)
and [system](https://github.com/SciPhi-AI/R2R/blob/main/py/sdk/sync_methods/system.py)
implementations. No live R2R installation was available for server verification.

### Installation, deployment and documentation — final checkpoint

- Reconciled locked dependencies and reader installation instructions. Improved the
  Windows launcher, provider discovery timeouts and startup/logging failure behavior.
- Updated Docker/Compose for the locked environment, Git/LibreOffice, non-root and
  read-only operation, writable session storage and host Ollama connectivity.
- Added container runtime checks and CI configuration. Strengthened the app-render
  smoke check to pass the browser-settings initialization boundary and assert that
  chat actually renders.
- Corrected README licensing references to the existing GPL-3.0 license without
  changing the license itself. Removed misleading universal-offline, automatic-
  correctness and resource/performance claims.
- Updated setup, usage, troubleshooting and contribution instructions to match
  actual controls, retries, reset, localStorage, model selection, R2R and logging.
- Replaced the expanding task list with the original scope and clearly optional
  extensions. This report is the cumulative handoff record.

## Verification record

| Check | Result and scope |
|---|---|
| Fresh installation, 2026-10-08 | Independent Python environment installed all 176 locked runtime dependencies from hashed requirements; dependency consistency passed |
| Final regression suite, 2026-10-08 | **184 tests passed**, including the 14 workflow tests and real fixtures for all 25 extensions |
| Static and compilation checks | Configured Ruff error checks and required Python compilation passed |
| Offline evaluation, 2026-10-08 | **42 passed, 0 failed, 34 live-answer checks explicitly skipped**; [report](../output/evaluation-release-mock/eval_report.md) |
| Streamlit clean-environment smoke | Health endpoint passed; temporary server stopped |
| Live compatible-provider transport | Chat returned `READY`; embedding returned 768 dimensions against local Ollama's compatible endpoint, using the LM Studio/TabbyAPI configuration paths |
| Compatible streaming transport | Real SDK streaming passed against a synthetic HTTP event stream with a custom model name |
| Earlier live quality, 2026-10-07 | Installed `llama3:latest`: **76/76 total checks, 34/34 live answers, 25/25 format questions**; [saved report](../eval_report.md) |
| Earlier Linux integration, 2026-10-06 | Container build, all 25 extractors, offline/read-only runtime, live Ollama, HTTPS and GitHub checks passed; [record](runtime-validation.md) |

Local final-run logs are retained in `tmp/release-regression-final.log`,
`tmp/release-workflows-transport.log`, `tmp/release-runtime.log` and
`tmp/release-mock.log`. The clean test environment was created under
`tmp/release-env-20261008`; it is separate from the project's existing environment.

## Subsequent demo-readiness fix: removing uploads

The upload-removal gap found after the wrap-up has been repaired. Removing all
uploaded files detaches their active index, clears upload status and prevents old
document conversation from being sent to the model again. Historical messages stay
visible. Source ownership protects an active website/repository index, and reupload
works normally. Removed R2R uploads become unqueryable while their ownership IDs
remain available for explicit Reset Project cleanup.

Regression coverage includes real TXT ingestion/removal/reupload, outgoing chat
context, preservation of other active sources and R2R query blocking. The run is
recorded separately in `tmp/upload-removal-regression.log`: **188 tests passed**.
Compilation, configured Ruff checks and the Streamlit health check passed; the
temporary server was stopped. Startup output is in `tmp/upload-removal-smoke.log`.

## What is not established by these checks

- The real browser opened the app and Settings, changed model/chunk controls and
  reloaded. Browser automation subsequently became unavailable, so restored values,
  upload and reset were not all rechecked through the actual browser. Streamlit
  workflow tests cover those application paths, but do not validate browser storage
  JavaScript end to end.
- Docker Desktop's engine was unavailable during the final 2026-10-08 rebuild
  attempt. The final code was verified in a clean Windows environment; the earlier
  Linux results are historical, not a claim that the final image was rebuilt.
- Actual LM Studio, TabbyAPI and R2R servers, AMD/ROCm hardware and hosted CI were
  not certified. The live compatible transport check used Ollama's compatible API.
- The full live quality benchmark was last run on 2026-10-07. The final wrap-up ran
  offline evaluation, workflow tests and live transport checks, not another full
  live-answer benchmark.
- Small synthetic fixtures do not establish accuracy for every real document.
  The small `qwen2.5:0.5b` model met only 3/34 complete answer checks; many failures
  involved missing citations, not failed file extraction. Prompt injection,
  incorrect answers and unsupported layouts remain possible.

OCR, email attachment extraction, broader human-reviewed evaluation and independent
security/third-party deployment certification are [optional extensions](todo.md),
not extra phases added to the agreed repair work.
