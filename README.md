# 🧠 DocMind AI — Private Offline RAG Assistant

> **Import files, GitHub repos, or websites — then chat with grounded answers. Everything runs locally. No data ever leaves your device.**

[![Quality](https://github.com/Amaann190/DocMind-AI/actions/workflows/quality.yml/badge.svg)](https://github.com/Amaann190/DocMind-AI/actions/workflows/quality.yml)
[![Docker Build](https://github.com/Amaann190/DocMind-AI/actions/workflows/main.yaml/badge.svg)](https://github.com/Amaann190/DocMind-AI/actions/workflows/main.yaml)
![Python](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-green)

> **Try it in 3 clicks:** `1` Upload files / paste GitHub or website → `2` Wait ~5 s (index built, cached) → `3` Ask anything — answers are cited from *your* docs. No account, no upload to cloud.

---

## Table of Contents

1. [Problem](#problem)
2. [Solution & Approach](#solution--approach)
3. [Novelty — What Makes This Different](#novelty--what-makes-this-different)
4. [System Architecture & Workflow](#system-architecture--workflow)
5. [Behind the Scenes — What Happens When You Add Content](#behind-the-scenes--what-happens-when-you-add-content)
6. [Plain RAG vs DocMind — Feature Matrix](#plain-rag-vs-docmind--feature-matrix)
7. [Tech Stack](#tech-stack)
6. [Features — Everything the App Does](#features--everything-the-app-does)
7. [Supported Documents & Sources](#supported-documents--sources)
8. [Modes & Options](#modes--options)
9. [Quick Start](#quick-start)
10. [Configuration](#configuration)
11. [Evaluation](#evaluation)
12. [Expected Outcomes](#expected-outcomes)
13. [Project Structure](#project-structure)
14. [Troubleshooting & Security](#troubleshooting--security)
15. [Roadmap](#roadmap)

---

## Problem

Teams and students who work with sensitive documents face a dilemma:

* **Cloud RAG is risky** — uploading contracts, research papers, or internal reports to a third-party API leaks private data and violates compliance.
* **Naïve local RAG is brittle** — plain vector search misses exact keywords (“30-day”), hallucinates when no evidence exists, breaks on Hinglish queries, and heats weak laptops during ingestion.
* **Tool sprawl** — useful knowledge lives in PDFs, Word docs, scattered CSVs, GitHub repos, and documentation sites, but most chatbots only accept one file type at a time.

**Goal:** one lightweight, fully offline assistant that ingests *any* of those sources, retrieves the *right* chunks reliably, and answers *only* from evidence.

---

## Solution & Approach

DocMind combines **Streamlit, LlamaIndex and Ollama** with hybrid keyword and vector retrieval. Model choice still affects reliability; the recorded document-answer checks favor `llama3:latest` over `qwen2.5:0.5b`.

| Design Choice | Why it matters (`code` ref) |
|---|---|
| **Hybrid BM25 + vector with RRF** | BM25 catches exact terms/numbers that dense vectors miss; RRF fusion costs only CPU (`utils/llama_index.py:260`) |
| **Evidence floor 0.5** | Weak vector scores (<0.5) need a BM25 keyword hit, otherwise the query is correctly *rejected* instead of hallucinated (`utils/llama_index.py:75`) |
| **Curated synonym expansion** | Short queries like “money back rules” widen to `refund` synonyms for BM25 only — vector query stays clean (`utils/llama_index.py:201`) |
| **Hyphen / Hinglish hygiene** | `30-day → 30 day`, single-letter tokens dropped, Hinglish fillers (`batao/kya/hai`) stripped (`utils/llama_index.py:184`) |
| **Title-aware chunks** | Every chunk is prefixed with its document title so title queries match all chunks and the LLM knows provenance (`utils/llama_index.py:141`) |
| **Exact duplicate filter** | Removes identical text from the same source/location while keeping changed facts and distinct sources (`utils/llama_index.py`) |
| **Grounded prompt + citations** | “Answer ONLY from context, quote numbers, cite `[n]`” + compact numbered context (`utils/llama_index.py:43`) |
| **Cache & Eco Mode** | Private session caches reuse embeddings; Eco trims batches/context for weak machines (`utils/llama_index.py`) |
| **Numeric word → digit** | `thirty days` ≠ `30 days` for BM25 | `thirty → 30` before stemming so `thirty days` matches `30 days` (`utils/llama_index.py:239`) |
| **Exact-phrase boost** | `"refund policy"` is bag-of-words | Quoted phrase gets +0.5 RRF if found verbatim (`utils/llama_index.py:358`) |
| **Tabular verbalization** | `id,info / 1,HR leave` is not a sentence | CSV/JSON rows → `Row 1: info is HR leave…` making tables retrievable (`utils/llama_index.py:175`) |
| **Code fence aware** | `requests.get(` split across chunks | ` ``` ` odd-count chunks merged before embed (`utils/llama_index.py:808`) |

Missing-evidence fallback: if retrieval returns 0 nodes the assistant says *“I could not find this information in the documents.”* and offers **Ask without documents** (`utils/ollama.py:528`, `components/chatbox.py:125`).

---

## Retrieval and evidence handling

DocMind combines local document readers, vector search, BM25 keyword retrieval, and
an explicitly grounded prompt. These mechanisms are tested individually; they do
not guarantee that every model answer is correct.

- Hybrid retrieval combines semantic matches with exact names, numbers, and codes.
- Short-query expansion includes phrases such as “money back”; vector search keeps
  the original wording.
- Empty retrieval returns a fixed missing-evidence response without invoking a model.
- Answers are asked to cite numbered sources; invalid citation IDs produce a warning.
- Exact duplicates are removed only within the same source/location.
- Session workspaces isolate uploaded files and cached indexes.
- Eco Mode reduces batch size and context/output budgets.

The earlier August “43/43, 100%” evaluation is superseded. It included structural
and mocked checks and did not establish general answer accuracy or freedom from
hallucinations. See [answer-quality findings](docs/answer-quality.md).

---

## System Architecture & Workflow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Sources    │     │  Ingestion   │     │    Retrieval     │
│  Local Files│────▶│  Validate    │────▶│  Vector (Ollama) │
│  GitHub Repo│     │  Load docs   │     │  + BM25 (rank-   │
│  Website    │     │  Chunk 256/32│     │    bm25) → RRF   │
│             │     │  Title+dedup │     │  Evidence floor  │
│             │     │  Embed batch │     │  Context budget  │
└─────────────┘     │  Index(cache)│     └────────┬─────────┘
                    └──────────────┘              │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│    UI       │◀────│  Generation  │◀────│    Query         │
│  Chat Box   │     │  Stream Chat │     │  Rewrite →       │
│  Suggestions│     │  Grounded    │     │  Multi-turn      │
│  Sources    │     │  Citations   │     │  History         │
└─────────────┘     │  No-halluc.  │     └──────────────────┘
                    └──────────────┘
```

**Ingestion flow** (`docs/pipeline.md`): validate model → load docs (LlamaIndex `SimpleDirectoryReader` + SSRF-guarded website fetch) → validate limits (≤300 docs, ≤4,194,304 text characters) → split → title/dedup → batched embed with progress & OOM shrink → `VectorStoreIndex` → streaming query engine + hybrid retriever → private session cache.

**Query flow** (`components/chatbox.py:56`, `utils/ollama.py:492`): rewrite query → vector+BM25 retrieve → filter by cutoff & evidence → build numbered context → prepend recent chat history (multi-turn) → `stream_chat` → render tokens + source chips.

**State:** `components/page_state.py:117` seeds session state; `sidebar.py:37` shows mode badges (RAG / R2R / Chat); `utils/browser_settings.py` persists preferences in `localStorage`.

---

## Behind the Scenes — What Happens When You Add Content

This is the “explain to a non-technical examiner” section — exactly what runs after you drag a file, paste a `owner/repo`, or add a website URL. The UI shows 4–5 stage chips; underneath this is what really happens.

### 1) Local Files — `components/tabs/local_files.py` → `utils/helpers.py` → `utils/llama_index.py` → `utils/rag_pipeline.py`

**You do:** sidebar → **Data Sources → Local Files → Upload** (up to 10 files, 25 MB each).

**System does:**

1. **Save safely** — filenames, extensions and upload sizes are validated. Resolved destinations must stay inside the session's operation directory. Limits are 10 files, 25 MB each and 100 MB total.
2. **Load** — the shared loader selects the configured reader for each of the 25 supported extensions. Repository exclusions skip binaries, archives and folders such as `.git` and `node_modules`. Unsupported, unreadable or empty files produce per-file diagnostics.
3. **Validate** — `validate_ingested_documents()` enforces **≤300 docs and ≤4,194,304 text characters** after preprocessing. Exceeding either limit produces an explicit error.
4. **Chunk** — an explicitly configured LlamaIndex splitter starts with 256 tokens and 32 tokens of overlap. Advanced settings calculate overlap from a percentage (12% of 256 gives 30). Overlap helps retain boundary context; it cannot guarantee every fact stays together. Changes take effect on the next ingestion.
5. **Enrich** — retain every nonempty chunk, including short codes. `_dedupe_exact_nodes()` removes only identical text from the same source/location, preserving different numbers, negations, and source identities. `_prepend_document_title()` adds a readable filename title to each chunk.
6. **Embed** — the selected embedding provider processes batches with progress updates. Ollama normally uses batches of 16 (Eco: 4). CUDA out-of-memory failures trigger smaller batches down to one; if that still fails, the app reports the failure and permits a retry.
7. **Index + cache** — `VectorStoreIndex(nodes=…, embed_model=…)` receives this session's model explicitly. Cache keys include embedding endpoint/backend, chunk settings, document boundaries and source metadata. Each session owns its cache and prunes only its own old entries (keep 5).
8. **Ready** — `create_query_engine()` uses the session's chat model and hybrid retriever. The operation's temporary files are removed on success or failure. Partial results retain their per-file warnings.

> **Seen as:** *files uploaded → documents loaded → embeddings generated → index ready* (kept in `st.session_state["file_ingestion_stages"]` so reruns don’t re-trigger).

### 2) GitHub Repo — `components/tabs/github_repo.py` → `utils/helpers.py:254`

**You do:** `Ashita-no-Kaushar/DocMind-AI` or `https://github.com/Ashita-no-Kaushar/DocMind-AI`.

**System does:**

1. **Normalize & validate** — `normalize_github_repo()` strips whitespace, parses URL, requires `https` + `github.com`, needs exactly `owner/repo` (2 path parts), strips trailing `.git`, then regex `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`. `https://gitlab.com/…` or `…/extra/path` → error. This is the same check `eval_harness.py:698` tests.
2. **Clone** — `clone_github_repo()` validates owner/repo and clones into a newly generated directory owned by this session, with a 120-second timeout. Cleanup removes only that clone, including on failure.
3. **Load** — the cloned folder is then processed exactly like Local Files (steps 2–8 above) — respecting `EXCLUDED_FILE_PATTERNS`, so `.git/` and `node_modules/` are never embedded.

> **Seen as:** *repository validated → repository cloned → files loaded → embeddings generated → index ready*.

### 3) Website — `components/tabs/website.py` → `utils/helpers.py:80`

**You do:** paste `https://docs.python.org/3/library/os.html` (up to 5 at once) → **+** → **Process**.

**System does:**

1. **Validate** — `validate_website_urls()` → `_validate_public_http_url()` per URL: scheme must be `https`, no `user:pass@`, hostname not in `BLOCKED_HOSTNAMES` (`localhost`, `metadata.google.internal`), **DNS → IP** via `getaddrinfo` and reject if IP `is_private / is_loopback / is_link_local` (prevents SSRF to `169.254.169.254` or `127.0.0.1`). Exceed 5 URLs → error.
2. **Fetch** — `load_website_documents()` uses an HTTPS connection pinned to a validated public IP, while checking TLS for the original hostname. It validates every redirect (at most three), accepts HTML/plain text, and caps each response at 5 MB with connection/read timeouts.
3. **Convert** — `html2text.html2text(html)` → clean markdown text → `Document(text=…, metadata={"source": url})`.
4. **Index** — same chunk/title/dedup/embed pipeline as above.

> **Seen as:** *websites fetched → content loaded → embeddings generated → index ready*.

### After indexing — how a question is answered

1. **Rewrite** — `_rewrite_query()` (`llama_index.py:248`): Porter-stem, split hyphens, drop filler words (`the/a/and`, plus Hinglish `batao/kya/hai`), produce `refunded purchases → refund purchas`.
2. **Retrieve** — vector search receives the original question. BM25+ uses normalized and expanded keywords; only actual keyword matches participate in reciprocal-rank fusion.
3. **Filter** — keyword matches can contribute independently of vector search. Vector-only candidates must pass the configured cutoff and evidence floor. An empty token corpus is valid and does not crash retrieval.
4. **Budget** — enforce Top K and the context size limit, shortening an oversized first chunk without changing stored evidence. Named-topic summaries use matching passages; only generic summaries use document openings.
5. **Generate** — number retrieved passages, mark them as untrusted evidence, and budget the complete prompt, current-corpus history and answer with a tokenizer and margin. Stream the model's answer and show source chips. The app does not invent missing citations.

See the [security review and session-isolation boundaries](docs/security.md).

---



## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| **UI** | Streamlit 1.62 (dark theme `#0E1117`) | Fast Python UI, no JS build |
| **RAG** | LlamaIndex 0.14 + `llama-index-readers-file/web` | Pluggable loaders, `VectorStoreIndex` |
| **LLM / Embed** | Ollama (`llama3:latest` / `nomic-embed-text:latest`) + OpenAI-compatible providers | Local inference or configured remote endpoints |
| **Retrieval** | `rank-bm25` + `nltk` Porter stemmer | Pure-Python, no torch, no extra model download |
| **Docs** | LlamaIndex readers, `openpyxl`, `xlrd`, `python-pptx`, `extract-msg`, LibreOffice | 25 file types; [setup](docs/setup.md) |
| **Infra** | Python 3.13, Pipenv, Docker (compose + ROCm variant), GitHub Actions (quality + Docker build) | Reproducible dev & deploy |
| **Observability** | Console logs, regression tests, evaluation reports | See recorded validation results |

No `torch`/`transformers` at runtime — removed for lightness (`Pipfile:6`).

---

## Tested capabilities and limits

DocMind supports 25 document extensions, local Ollama models, compatible servers,
GitHub repositories, and public HTTPS pages. Extraction support and answer quality
are separate checks: a file can load correctly while a small model still gives an
incorrect, incomplete, or uncited answer.

Use the reported model-specific evaluation results when choosing a chat model.
Local operation requires installed dependencies and models; website/repository
imports and remote model endpoints involve network access.

---

## Features — Everything the App Does

### Ingestion Sources (sidebar **Data Sources**)

* **Local Files** — drag & drop, 25 MB/file, CSV/TSV/JSON/JSONL/XML/XLS/XLSX/PDF/DOC/DOCX/PPT/PPTX/ODT/RTF/EPUB/EML/MBOX/MSG/TXT/MD/Markdown/HTML/HTM/MHTML/IPYNB (`utils/helpers.py:19`)
* **GitHub Repo** — `owner/repo` or `https://github.com/owner/repo`, SHA-clone `--depth 1`, stale-checkout handling (`utils/helpers.py:254`)
* **Website** — up to 5 URLs, HTTPS-only, redirect + size + SSRF guards, HTML→text via `html2text` (`utils/helpers.py:108`)
* Exclusions: binaries/archives/images (`*.png, *.zip, *.exe, *.mp4, node_modules …`) (`utils/llama_index.py:689`)
* Stages shown live: *validated → cloned/fetched → loaded → embedded → ready* (`components/tabs/sources.py:17`)

### Retrieval & Chat

* **Two modes auto-routed** — RAG (with `query_engine`) vs direct LLM (`components/chatbox.py:58`)
* **Hybrid retriever** with top-k, similarity cutoff, context budget (`utils/llama_index.py:260`)
* **Evidence-based prompts** requesting citations `[n]`, with numbered sources retained under each answer and in Word exports; correctness still depends on the model
* **Evidence gate** + “Ask without documents” fallback when retrieval finds no evidence
* **Multi-turn memory** — last RAG context includes recent history (`utils/ollama.py:115`)
* **Streaming** token-by-token via `write_stream`

### Settings (`Settings` tab — `components/tabs/settings.py:119`)

| Group | Controls |
|---|---|
| **Chat** | Provider (Ollama / OpenAI / LM Studio / TabbyAPI) → Chat Model dropdown + Refresh; Server URL & API key when non-Ollama |
| **Document Search** | Embedding Model dropdown + Refresh |
| **Answer Style** | 6 presets: Concise / Balanced / Detailed / Bulleted / Technical / Simple-ELI5 → prompt preview (collapsed) |
| **Preferences** | Eco Mode (batch 4, 256 tokens, ≤3 chunks, 3200-char budget) + Show advanced controls |
| **Advanced** (when on) | Sources per answer, Relevance threshold, Creativity, Chunk Size/Overlap + live token count — **see drill-down below** |
| **External RAG (R2R)** | Optional `utils/r2r.py` server (`http://localhost:7272`), health check, doc IDs |
| **Export** | Download chat as `.docx` (`chat_history_docx`) |

Sidebar extras: **mode badge** (Chat / RAG / R2R), **Clear Chat & Reset** expander, browser-settings persistence.

#### Advanced Settings — In Detail (hidden until “Show advanced controls” is on)

> All of these are **live** — change them and the *next* query uses the new value (chunk settings need a re-ingest). They are deliberately hidden by default so a new user sees only 3 cards.

| Control | Key (`page_state.py`) | Default | Range | What it does — in plain words | When to tweak |
|---|---|---:|---|---|---|
| **Sources per answer** | `top_k` | `3` | 1–10 slider | How many document chunks are glued into the prompt. More = broader context but more noise/hallucination risk. Eco caps at 3. | Raise to 5–7 for long reports where facts are scattered; lower to 1–2 for invoices/Q&A where one chunk holds the answer. (`utils/llama_index.py:319`) |
| **Relevance threshold** | `similarity_cutoff` | `0.30` | 0.00–1.00 (0.05 step) | Minimum vector score to keep a chunk. `0` = no filter. Higher = stricter. After that, the **evidence floor** (`0.5`) still requires a BM25 keyword hit for weak scores. | Raise to 0.4–0.5 if you see irrelevant sources; lower to 0.15 if good chunks are being dropped (but watch hallucinations). (`utils/llama_index.py:376`) |
| **Creativity** | `temperature` | `0.4` | 0.0–1.5 (0.05) | Sampling randomness. Lower values favor more focused output; they do not guarantee determinism. | Use lower values for factual answers and higher values for drafting. |
| **Chunk Size** | `chunk_size` | `256` tokens | number, 64–8192 | Tokens per piece before embedding. Smaller pieces usually create more vectors. | Adjust for document structure, then **Reprocess files**. |
| **Chunk Overlap** | `chunk_overlap_pct` → `chunk_overlap` | `12%` → `30` tokens in Advanced | 0–50% slider | Shared context between neighboring chunks, calculated as `chunk_size * pct // 100`. Initial overlap before Advanced recalculation is 32 tokens. | Increase if relevant context crosses boundaries, then re-ingest. |
| **Eco Mode** | `eco_mode` | `off` | toggle | Shrinks embedding batches, answer length and retrieval context. Performance depends on the model and hardware. | Use when resource use matters more than longer answers/context. |
| **R2R Base URL / API Key** | `r2r_base_url` / `r2r_api_key` | `http://localhost:7272` / `` | inside collapsed *External RAG* expander | When on, uploads go to an external R2R server instead of local LlamaIndex — less local RAM/disk. | Only if you run the R2R stack separately. (`utils/r2r.py`) |

Allowlisted preferences persist in browser `localStorage`; credentials do not. Persistence requires browser storage to be available. Reset via **Clear Chat & Reset → Reset Project**. Tracked R2R documents are deleted before local reset; a failed remote deletion is shown and can be retried.

### Performance & Safety

* **Eco Mode** for hot/weak machines (`components/tabs/settings.py:218`)
* **Index cache** — private per-session storage, keep 5, keyed by documents, sources and embedding configuration (`utils/llama_index.py`)
* **OOM retry** — halves embedding batches on CUDA OOM and reports failures that remain at batch size one
* **Security** — GitHub URL normalize & reject non-github, website SSRF/IP block, upload name/size limits, `SAFE_UPLOAD_NAME_PATTERN` (`utils/helpers.py`)

---

## Supported Documents & Sources

**25 extensions:** `.csv .doc .docx .eml .epub .htm .html .ipynb .json .jsonl .markdown .mbox .md .mhtml .msg .odt .pdf .ppt .pptx .rtf .tsv .txt .xls .xlsx .xml`

Install the [reader dependencies and LibreOffice](docs/setup.md) for all formats.
See [extraction scope and known limits](docs/usage.md#local-files). Automated
real-file extraction checks live in `tests/test_document_readers.py`.

Plus: any GitHub repo (public, shallow clone) and up to 5 HTTPS websites at once.

Upload limits: 10 files, 25 MB/file, 100 MB total; ingestion limits: 300 docs, 4,194,304 text characters after preprocessing — enforced with clear errors.

---

## Modes & Options

| Mode | When | What happens |
|---|---|---|
| **Chat** | No index | Direct LLM (`utils/ollama.py:426`) with system prompt + chat history |
| **RAG** | After ingesting files/repo/sites | Hybrid retrieval → grounded prompt → cited answer |
| **R2R** | Enabled and files successfully uploaded to the current R2R server | Local Files use the external server; chat is restricted to this session's tracked document IDs. GitHub and Website imports are unavailable in this mode. |

Other toggles: **Answer tone** quick selector in chat (`components/chatbox.py:58`) mirrors Settings; **Directly import** caption reminds users how grounding works.

---

## Quick Start

**Prereqs:** Ollama running, Python 3.13, at least one chat + embedding model:

```bash
ollama pull llama3:latest
ollama pull nomic-embed-text:latest
ollama list
```

**Local (Pipenv):**

```bash
pip install pipenv
pipenv sync
pipenv run streamlit run main.py
# open http://localhost:8501
```

**Docker:**

```bash
docker compose up --build -d --wait
# app at http://localhost:8501
# point Ollama endpoint to host.docker.internal:11434 if Ollama is on host
```

Change Ollama endpoint in **Settings → Chat** if needed. First ingestion builds the index; unchanged inputs can reuse a session cache. Actual timing depends on the model, hardware and documents.

---

## Configuration

* **Ollama endpoint** default `http://localhost:11434`, editable in Settings and persisted in `localStorage`.
* **Chunking** 256 / 32 (12 %) — tweak in Advanced; next ingestion uses new values.
* **Top K / cutoff / temperature** — live, next query uses new values (no re-ingest).
* **Theme** dark (`#0E1117` / `#161B26` / violet `#8B5CF6`) in `.streamlit/config.toml:7`.

---

## Evaluation

The harness reports **passed, failed, and skipped** separately. Offline control checks
use stable hash embeddings; live checks require the requested models and never
silently fall back to mocks. A failed check produces a nonzero exit status.

```bash
pipenv run python eval_harness.py --mock --out output/evaluation-mock
pipenv run python eval_harness.py --chat-model llama3:latest --out output/evaluation-live
pipenv run python eval_harness.py --suite retrieval --out output/retrieval
```

Live answer checks cover exact facts, citations, conflicting sources, missing evidence,
document instructions, follow-ups, and all 25 formats. JSON results retain actual
answers, sources, per-check decisions, timings, and model names for review. Skipped
live checks in mock mode do not measure answer quality.

[Current findings and limitations](docs/answer-quality.md) explain the model comparison.
See [completed work and release verification](docs/completed-work.md) for the original repair scope and final workflow checks.
The generated `eval_report.md` and `eval_results.json` at the repository root contain
the latest full live run. Run unit tests with
`pipenv run python -m unittest discover -s tests`.

---

## Expected Outcomes

* **Privacy:** local model inference is available; website/repository imports and remote endpoints use the network.
* **Reliability:** evidence checks and citation prompts reduce errors; verify important answers against their sources.
* **Usability:** non-technical flow — add docs → chat; 3 steps in the welcome card (`components/page_state.py:18`).
* **Efficiency:** session index caching avoids unnecessary re-embedding; Eco Mode reduces compute budgets.
* **Breadth:** 25 formats + repos + sites in one index — no tool switching.

For a final-year project the *novelty is system design* (hybrid + evidence gating on a tiny 0.5B model), not model size — an honest, defensible story.

---

## Project Structure

```
.
├── main.py                     # bootstrap: header → messages → sidebar → chatbox
├── components/
│   ├── header.py               # branded title + tagline
│   ├── page_config.py          # dark theme, centered layout, chrome hiding
│   ├── page_state.py           # WELCOME_MESSAGE, session-state seeding
│   ├── sidebar.py              # Data Sources / Settings tabs + mode badge + Clear & Reset
│   ├── chatbox.py              # streaming, citations, tone pills, suggestions
│   └── tabs/
│       ├── sources.py / local_files.py / github_repo.py / website.py
│       └── settings.py         # providers, models, style, eco, advanced, R2R, export
├── utils/
│   ├── llama_index.py          # index, hybrid retriever, embeddings, cache, dedup
│   ├── ollama.py               # LLM factories, chat/context_chat, history trimming
│   ├── helpers.py              # upload/URL/GitHub validation, file handling
│   ├── rag_pipeline.py         # ingestion pipeline orchestration
│   ├── browser_settings.py     # localStorage persistence
│   └── r2r.py                  # optional RAG-to-Riches backend
├── tests/                      # regression tests (ingestion, security, settings, etc.)
├── docs/                       # pipeline / setup / usage / contributing / troubleshooting
├── eval_harness.py             # comprehensive 6-suite eval (43 tests)
├── eval_report.md              # generated report (this section)
├── eval_results.json           # generated JSON
├── Pipfile / Pipfile.lock      # deps (no torch)
├── .streamlit/config.toml      # dark theme + upload limit
├── Dockerfile + docker-compose.yml
└── .github/workflows/quality.yml + main.yaml  # tests + Docker build
```

---

## Troubleshooting & Security

**Common issues → docs:**

* **Ollama not running / model not found** → [troubleshooting](docs/troubleshooting.md) — check `http://localhost:11434`, `ollama list`, installed chat/embedding models, and Settings → Connection.
* **No usable content / empty index** → check the per-file error report. Empty files and scanned PDFs without a text layer need readable text or OCR before upload; short nonempty facts are retained.
* **CUDA OOM during embed** → Eco Mode on, or lower `Chunk Size`; batch auto-halves (`utils/llama_index.py:540`).
* **Website fails / SSRF block** → only `https`, no `localhost/metadata`, ≤5 URLs, ≤5 MB, HTML/plain only (`utils/helpers.py:80`). Use a public URL.
* **GitHub clone fails** → use `owner/repo` or `https://github.com/owner/repo`, check `git` is installed, ensure repo is public (`utils/helpers.py:254`).
* **Slow answers / hot laptop** → turn on **Eco Mode** (`Settings → Preferences`), split 300-page PDFs into chapters.

**Security model → `SECURITY.md`:**

* Uploads validated by `SAFE_UPLOAD_NAME_PATTERN` + extension allow-list + size caps (10 files / 25 MB / 100 MB total).
* Websites: SSRF-guarded via DNS→IP check (`_is_blocked_ip`), blocked hosts, redirect & size limits.
* GitHub: strict `owner/repo` regex, only `github.com` over `https`.
* No eager torch imports in the tested app modules; local inference is supported alongside network-backed sources.

---

## Roadmap

* [ ] Rerank cross-encoder (optional, still no torch by default)
* [ ] More export formats (markdown, PDF)
* [ ] Collaborative sharing of cached indexes
* [ ] Optional OCR for scanned PDFs (pluggable, off by default)

---

## License

GNU GPL version 3 — see [LICENSE](LICENSE). This description follows the existing license file; the license text has not been changed.

> Built with Streamlit · LlamaIndex · Ollama · rank-bm25 · NLTK · python-docx.
