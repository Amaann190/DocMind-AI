# DocMind AI

**A React workspace for chatting with documents, powered by a Python FastAPI backend, LlamaIndex and Ollama.**

Add sources, ask questions, and inspect the passages supporting each answer. The frontend is built with React and Vite; FastAPI serves both the production website and its API.

## Features

- Light/dark mode, responsive layouts, collapsible and resizable side panels.
- Saved conversations with topic-based names, rename, search, reopen and delete.
- Streaming answers, stop/regenerate, copy and Word export.
- Individual source preview, retry/reindex, replacement and removal.
- Hybrid keyword/vector retrieval with citation passages and available page labels.
- Local Ollama models, OpenAI-compatible endpoints, and optional R2R integration.
- Private session workspaces, upload/path limits, public HTTPS validation and scoped repository imports.

## Run locally

Requirements: **Python 3.13**, **Node.js 22**, Git and an Ollama server.
Install LibreOffice for legacy DOC/PPT support; Calc is also needed to generate legacy spreadsheet test fixtures.

```bash
python -m pip install pipenv
pipenv sync --dev
cd frontend
npm ci
npm run build
cd ..
ollama pull llama3:latest
ollama pull nomic-embed-text:latest
pipenv run python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765**. Select installed models in Settings.
On Windows, `./run.ps1` starts the same app after installation/build; use
`./run.ps1 -Port 8766` if the default port is occupied. `run-react.ps1` remains
a compatibility shortcut to that launcher.

For frontend development, run the backend above and `npm run dev` inside
`frontend` in another terminal. Open http://localhost:5173; Vite proxies API
requests to port 8765. `npm run preview` alone does not run the Python API.

## Supported sources

25 file extensions:

```text
csv doc docx eml epub htm html ipynb json jsonl markdown mbox md
mhtml msg odt pdf ppt pptx rtf tsv txt xls xlsx xml
```

Also import public HTTPS pages and public GitHub repositories using `owner/repo`
or `https://github.com/owner/repo`.

- Up to 10 files per upload, 25 MB per file and 100 MB retained upload data per workspace.
- The local index accepts up to 300 extracted document units and 4 MB of text.
  Pages, slides and email messages can each count as a unit.
- Scanned documents/image text require OCR before import. Email attachments are not extracted.
- XLS/XLSX retain sheet names. XLSX preserves formulas and saved results; a missing
  formula result is explicitly marked. DocMind does not calculate workbook formulas.
- Failed files stay visible for retry or replacement; they are not counted as ready.

## Storage and privacy

Chats, titles and citation passages are stored in local SQLite. Sources and indexes
are held in the active backend session and must be uploaded again after a restart.
Saved chats share the current source collection; reopening one does not restore its old files.
Browser preferences use localStorage; model credentials are excluded from persisted settings.

The default database is `data/react-history.sqlite3`. Set `DOCMIND_DATA_DIR` to
choose another directory. `DOCMIND_OLLAMA_ENDPOINT` sets the default model endpoint.

Ollama keeps inference at the configured Ollama server. Selecting another provider sends
requests to that provider. This app is intended for local use with a **single API worker**,
not unauthenticated public hosting. See [security](docs/security.md).

## Docker

```bash
docker compose up --build -d --wait
```

Open http://localhost:8765. The image builds React and runs FastAPI. Compose connects
to Ollama on the host through `host.docker.internal:11434`. Chat history persists
in the `docmind-data` volume; active source indexes do not survive a restart.
The app runs as a non-root user with a read-only application filesystem.

Use `DOCMIND_PORT`, `DOCMIND_CPUS`, and `DOCMIND_OLLAMA_ENDPOINT` for overrides.
Stop with `docker compose down`; adding `-v` also deletes the stored chat volume.
The compatibility ROCm compose file uses the same app; GPU acceleration belongs to Ollama.

## Verification

```bash
pipenv run python -m unittest discover -s tests
pipenv run python -m compileall -q backend utils
pipenv run ruff check . --select E9,F63,F7,F82
pipenv run python eval_harness.py --mock --out output/react-evaluation
cd frontend
npm run build
npx playwright install chromium
npm run test:ui
```

Browser tests expect the running app at port 8765. Set `DOCMIND_LIVE=1` to include
the optional Ollama workflow. Mock evaluation verifies software behavior, not model answer quality.

## Project structure

| Path | Purpose |
|---|---|
| `frontend/` | React/Vite website and Playwright tests |
| `backend/app.py` | FastAPI, sessions, sources, chat streaming and export |
| `backend/history.py` | SQLite conversation storage |
| `utils/` | Readers, validation, retrieval, model clients and request state |
| `tests/` | Backend and ingestion regressions |
| `eval_harness.py`, `eval_quality.py` | Offline checks and optional live-answer evaluation |

## Documentation

[Setup](docs/setup.md) · [Usage](docs/usage.md) · [Architecture](docs/pipeline.md) ·
[React workspace](docs/react-workspace.md) · [Troubleshooting](docs/troubleshooting.md) ·
[Answer quality](docs/answer-quality.md) · [Contributing](docs/contributing.md)

Licensed under the [MIT license](LICENSE); original copyright and attribution are retained.
