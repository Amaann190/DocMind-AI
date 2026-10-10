# DocMind Workspace: React edition

This is a separate checkout on branch `react-redesign`. The original project folder
and GitHub `main` remain unchanged. No migration changes have been pushed to GitHub.

## Run

Prerequisites: Python 3.13, Node.js 22.12 or later, Pipenv and Ollama. LibreOffice,
as described in [setup](setup.md), is still needed for legacy Office formats.

From this checkout:

```powershell
$env:PIPENV_VENV_IN_PROJECT = '1'
pipenv sync --dev
cd frontend
npm ci
npm run build
cd ..
./run-react.ps1
```

Open **http://127.0.0.1:8765**. The launcher uses one server for the built React
application and its API. It does not stop or replace Streamlit on port 8501.
Use `./run-react.ps1 -Port 8766` to choose another port.

On other platforms, after building the frontend:

```bash
pipenv run python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

For frontend development, run that API command in one terminal and `npm run dev`
inside `frontend` in another. Vite serves port 5173 and proxies `/api` to 8765.
`npm run preview` previews assets only; use the Python server for a working app.

Select installed model names in Settings. The tested defaults are `llama3:latest`
and `nomic-embed-text:latest`. Provider presets do not install models or servers.

## Design and features

- A warm ivory canvas, dark olive navigation, orange accents and locally bundled
  DM Sans/Manrope typography. No Streamlit widgets, reruns or browser component
  are used by the React interface.
- A dedicated conversation view, source library and settings page. The source rail
  gives access to extracted text; answer citations open their retrieved passages.
- File selection and drag-and-drop for all 25 existing supported extensions,
  HTTPS website import, public GitHub import, and an explicitly labeled sample.
- Incremental streamed answers, copy, Word export, answer style and model controls.
- Partial-import warnings, progress, reset, source removal and conversation clearing.
- Responsive navigation and composer, keyboard-accessible dialogs, reduced-motion
  support and recovery when stored preferences cannot be restored.
- OpenAI-compatible model presets and optional R2R file upload/query integration.

Each import **replaces** the current source collection. Removing sources clears the
index and excludes previous document conversation from future model context while
leaving its historical messages visible. Starting a new conversation keeps sources.
Changing embedding/server configuration clears the collection to prevent incompatible
indexes. Export before resetting if you want to keep the conversation.

R2R uses the existing owned-document-ID contract. Source removal/reset attempts to
delete its tracked server copies. Failed remote cleanup retains ownership IDs and
blocks queries; restore the original server and retry. Restarting the API loses
in-memory remote ownership tracking, so clean up R2R sources before stopping it.

## Architecture and boundaries

- `frontend/`: React, Vite, Lucide icons, React Markdown, self-hosted fonts and
  Playwright UI tests. `package-lock.json` pins the frontend dependency tree.
- `backend/app.py`: FastAPI endpoints for session state, settings, models, ingestion,
  streaming, source removal and export. It serves `frontend/dist` in production mode.
- `utils/runtime.py`: a small context-local state adapter. Shared reader/retrieval
  code reads the current API session; legacy Streamlit calls retain their own state.
- `utils/document_readers.py`, `utils/helpers.py`, `utils/llama_index.py` and
  `utils/ollama.py`: reused extraction, validation, retrieval and generation logic.

The API is a **local desktop server**, not an authenticated public hosting service.
Run a single worker on loopback. Cookie-selected sessions have separate models,
documents, locks and temporary directories. API mutations require an application
header; cross-origin requests and unexpected Host headers are rejected. Validation
retains upload/path/archive limits and public-HTTPS guards. These controls are not
a substitute for authentication if deploying to a shared network.

Chat and sources stay in server memory. Local sessions expire after eight idle hours
when another session initializes; sessions with pending R2R cleanup are retained.
Restarting the API drops local workspace state. Non-secret preferences persist in
browser localStorage; API keys stay in server memory and are excluded from state
responses and browser storage. There is no account system or cloud conversation sync.
Fonts and frontend assets are bundled locally. Document content goes to the model
endpoint you choose; websites, GitHub and remote providers require networking.

## Verification

```powershell
pipenv run python -m unittest discover -s tests
pipenv run python -m py_compile backend/app.py utils/runtime.py main.py components/page_state.py components/tabs/settings.py utils/browser_settings.py utils/ollama.py
cd frontend
npm run build
npx playwright install chromium
npm run test:ui
# Optional live test: requires the API running plus installed Ollama models.
$env:DOCMIND_LIVE = '1'
npm run test:ui
```

The browser suite expects the application at port 8765. Set
`PLAYWRIGHT_CHROME_PATH` to use a specific local Chrome executable instead of
Playwright's browser.

On 2026-10-10, **194 Python tests passed** in the final locked environment, with
successful compilation, static checks and dependency consistency. **All three
browser tests passed**, including the optional live Ollama workflow.

Desktop/mobile navigation, persisted settings, import dialogs,
streamed answer display and source previews were checked in a real browser. A live
TXT upload through Ollama returned the correct $24,000 budget with a source reference;
Word export and source removal passed. The screenshot evidence is saved locally in
`output/react-*.png` (not committed). API regressions cover real extraction/indexing
with controlled models, isolation, invalid paths/origins, settings validation,
concurrent requests and remote cleanup failure. See `react-api-tests.log`,
`react-regression.log` and frontend test results for the local runs.

The existing format/retrieval tests remain applicable. No new claims are made about
live R2R/LM Studio/TabbyAPI servers, Docker deployment or hosted CI. Their independent
verification is unchanged by a UI migration. OCR and arbitrary-document accuracy
remain outside the verified scope.

Implementation references: [React with Vite](https://react.dev/learn/build-a-react-app-from-scratch),
[FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/) and
[streaming responses](https://fastapi.tiangolo.com/advanced/stream-data/).
