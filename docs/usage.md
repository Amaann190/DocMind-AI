# Using DocMind

## Quick Start

1. Open Settings and confirm the Ollama endpoint.
2. Select a valid chat model.
3. Select an embedding model, such as `nomic-embed-text:latest`.
4. Import data from local files, a GitHub repository, or websites.
5. Once ingestion completes, ask questions in the chat box.

Data import controls stay disabled until the required model settings are valid.

## Settings

Settings are stored in browser `localStorage` and restored on the next visit from the same browser. Chat history is not persisted this way; use the Export Data section to download it.

### Ollama

| Setting | Description | Default |
| --- | --- | --- |
| Ollama Endpoint | Ollama API base URL. Empty values are ignored and fall back to `http://localhost:11434`. | `http://localhost:11434` |
| Chat Model | Installed Ollama model with `completion` capability. Valid saved choices are retained. | Preference order: `gemma4:latest`, `llama3:8b`, `llama3:latest`, `llama2:7b`, then the first discovered model. Tested recommendation: `llama3:latest`. |
| Refresh Models | Reloads chat and embedding model lists for the current endpoint. | |
| Top K | Number of most similar chunks to retrieve for each query. Applies to the next query immediately. Advanced setting. | `3` |
| Similarity Threshold | Minimum vector similarity score for a chunk to be used. Higher = stronger matches only, lower = more recall, `0` = disabled. Applies to the next query immediately. Advanced setting. | `0.3` |

### Embeddings

| Setting | Description | Default |
| --- | --- | --- |
| Embedding Model | Installed Ollama model with `embedding` capability. | `nomic-embed-text`, when available |
| Chunk Size | Maximum tokens per indexed chunk; numeric input, 64–8192. Applies on reprocessing. | `256` |
| Chunk Overlap | Token overlap. Advanced controls calculate it as a percentage of chunk size. | Initially `32`; Advanced defaults to 12%, giving `30` at size 256. |

Ollama, OpenAI, LM Studio and TabbyAPI are provider presets. The latter three use
the OpenAI-compatible chat/embedding API with the model names supplied in Settings.
The server must actually provide both endpoints for document indexing. Selecting a
preset does not install a server or models. Creativity changes apply to the next response.

R2R mode uses its own server models and accepts **Local Files only** in this app.
Repository and website controls explain how to switch back to local indexing.
R2R queries are limited to this session's uploaded IDs. Changing the R2R address or
credential cannot reuse another server's IDs. An upload waits for synchronous server
ingestion before showing ready. R2R's own format support is separate from the 25 local readers.

## Data Sources

### Local Files

Removing all files from the uploader detaches its active document index. Earlier
messages remain visible, but are no longer sent as context for future answers.
An active website or repository index is preserved. Reuploading files processes
them again. In R2R mode, removal blocks further queries against those files;
use Reset Project to delete the tracked copies from the remote server.

Supported upload extensions (25):

| Content | Extensions |
| --- | --- |
| Documents and books | `pdf`, `doc`, `docx`, `odt`, `rtf`, `epub` |
| Presentations | `ppt`, `pptx` |
| Tables and structured data | `csv`, `tsv`, `xls`, `xlsx`, `json`, `jsonl`, `xml` |
| Text, web pages, notebooks | `txt`, `md`, `markdown`, `html`, `htm`, `mhtml`, `ipynb` |
| Email | `eml`, `mbox`, `msg` |

Legacy `doc` and `ppt` require [LibreOffice installation](setup.md). Other readers
are installed by `pipenv sync`. The same readers are used for repository files.

Extraction uses existing document text and spreadsheet values. Scanned pages and
images require OCR, which is not included. Password-protected files must be unlocked
before upload. Email bodies and headers are read; attached documents are not imported.
Notebook source and saved text outputs are read without executing code.

JSON and JSONL preprocessing keeps all records and the full original text. CSV/TSV
also retain their complete source, including extra values without column names.
Short nonempty facts are indexed. Duplicate filtering removes only identical text
from the same source and location, preserving changed numbers and conflicting facts.

If some files cannot be read, the remaining files are indexed and a persistent warning
lists each skipped file and its reason. Answers cover only the successfully read files.
If every file is unreadable or empty, ingestion fails with details. Format and indexing
checks do not guarantee answer accuracy for every question.

If an import fails, Settings remains accessible. Fix the connection or file and
choose **Reprocess files**; the app does not retry the same failed upload on every
rerun. That button also applies changed embedding/chunk settings to existing uploads.

Upload limits:

- Up to 10 files per upload
- 25 MB per file
- 100 MB total per upload

Each import uses its own temporary directory inside the current session's workspace.
Uploads are removed after success or failure. Re-uploading unchanged files can reuse
that session's index; a new session builds its own index. Reset clears only the current
session's files and caches. Old project-level `data/` and `.index_cache/` folders are
no longer used or automatically deleted.

### GitHub Repositories

The GitHub source accepts either:

- `owner/repo`
- `https://github.com/owner/repo`

Only `github.com` repository URLs are supported. URLs must point directly to a repository;
extra path segments and `.`/`..` names are rejected. Each shallow clone gets a unique
directory in the current session and is removed after processing, including failure.
Links outside the selected source are rejected. Source discovery allows at most 1,000
files, 25 MB per file and 100 MB total; loaded text still has the ingestion limits in
[the pipeline documentation](pipeline.md).

### Websites

Website ingestion accepts up to 5 public HTTPS URLs at a time. If you enter a hostname without a scheme, DocMind adds `https://`.

Guardrails:

- Only HTTPS URLs are allowed.
- Embedded URL credentials are rejected.
- Local, private, link-local, metadata, multicast, reserved, and unspecified network addresses are blocked.
- Redirects are followed up to 3 times.
- Responses must be HTML or plain text.
- Website response bodies are limited to 5 MB per URL.
- Each connection uses the validated public IP, preserving certificate and hostname verification.
- Redirect targets are checked again. Website fetching does not use environment proxies or stored credentials.

## Retrieval and sources

Vector search receives the original question. Keyword search uses normalized terms
and can find exact codes even when vector search omits their chunks. Named-topic
summaries use matching evidence; generic summaries use document openings within
the selected Top K and context budget. Large evidence blocks are shortened without
changing the stored source text.

RAG prompts reserve room for instructions, recent history and the answer using a
tokenizer and a safety margin. Token counts still vary between model families.
Starting a new import prevents earlier documents' conversation history from being
used as evidence for the new corpus. Retrieved passages are marked as untrusted
evidence. The app no longer inserts an automatic citation when the model omits one.

Numbered source references are stored with each answer and remain visible on reruns
and in Word exports. Search scores are not shown as answer-confidence percentages.
The **Ask without documents** button offers a separate general answer after a
retrieval miss. Interrupted responses retain partial text with an error notice.

## Clear Chat and Reset

Clear Chat removes conversation history and its follow-up context, while retaining
the active document collection. Reset Project clears this session's files, caches,
source inputs, credentials and settings, and replaces the upload widget so old files
are not silently imported again. It also deletes tracked R2R uploads at their original
server. If that cleanup fails, reset pauses and retains the remaining IDs for retry.
Closing the browser is not a request to delete remote R2R documents; reset first when
remote cleanup is required. Only one local collection is active at a time.

## Export Data

Use **Settings → Export → Download chat (.docx)** to download the transcript with numbered sources.
