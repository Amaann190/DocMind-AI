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
- A moon/sun control in the header switches light and dark mode. The first visit
  follows the device theme; an explicit choice is saved locally and applied before
  rendering on later visits. Theme switching also works with browser storage blocked.
- A dedicated conversation view, source library and settings page. The source rail
  gives access to extracted text; answer citations open their retrieved passages.
- File selection and drag-and-drop for all 25 existing supported extensions,
  HTTPS website import, public GitHub import, and an explicitly labeled sample.
- Incremental streamed answers, copy, Word export, answer style and model controls.
- Automatically saved conversations with rename, content/title search, reopen and delete.
- Individual source retry/reindex, replacement and removal from each source preview.
  Failed files stay visible for recovery; a failed replacement keeps the working source.
- Stop saves partial output; regenerate replaces the latest answer without duplicating
  its question. Stop takes effect at the next provider response/stream boundary, so a
  blocked provider request can take until its timeout to release the workspace.
- Citation previews highlight the retrieved passage and show reader-provided page
  labels where available. They are text previews, not rendered PDF pages.
- Partial-import warnings, progress, reset and source removal.
- Responsive navigation and composer, keyboard-accessible dialogs, reduced-motion
  support and recovery when stored preferences cannot be restored.
- Both side panels can be hidden and reopened. Navigation content scrolls independently
  with My workspace pinned below it; the source panel scrolls and becomes a closable
  drawer on narrow screens. The chat area fits the space remaining below status messages.
- Desktop panel edges support dragging and keyboard arrows/Home/End. Width preferences
  persist locally; narrow screens use the existing fixed-width drawers.
- OpenAI-compatible model presets and optional R2R file upload/query integration.

Imports **add** to the current source collection. Removing or replacing a source
rebuilds the remaining local index before committing the change and excludes previous
document conversation from future model context. Historical messages remain visible.
Starting a new conversation saves the previous one and keeps sources. All saved chats
share the current source library; reopening does not restore an old document collection.
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
  conversations, streaming, source management and export. It serves `frontend/dist`.
- `backend/history.py`: Python standard-library SQLite storage for conversation titles,
  messages and citation passages. No new database service or dependency is required.
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

Active sources, uploaded bytes (at most 100 MB per workspace) and indexes stay in memory.
Local sessions expire after eight idle hours
when another session initializes; sessions with pending R2R cleanup are retained.
Restarting the API drops source state: re-add documents for grounded follow-up answers.
Saved titles, messages and citation passages survive in `data/react-history.sqlite3`,
excluded from Git. This is unencrypted local application data. Each browser's HttpOnly
cookie selects its private history; clearing that cookie loses access to its saved chats.
Delete individual chats or reset the workspace to delete that browser's stored history.
Non-secret preferences and panel widths persist in
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

On 2026-10-10, **199 Python tests passed**, with successful compilation and a
production frontend build. **All six browser tests passed**, including the optional
live Ollama workflow and its individual source reindex, replacement and removal checks.
The locked environment's dependency consistency was verified during initial setup.

The dark-mode follow-up passed seven browser checks (the live-model test was not
rerun for this visual change), including device-theme defaults, saved preference,
keyboard switching, unavailable browser storage, dark dialogs and mobile layouts.

Desktop/mobile navigation, persisted settings, import dialogs,
streamed answer display and source previews were checked in a real browser. A live
TXT upload through Ollama returned the correct $24,000 budget with a source reference;
Word export and source removal passed. Saved-chat rename/search/reopen/delete, retained
panel widths, pointer/keyboard resizing, stop/regenerate controls, and highlighted
page-labelled citations were also exercised. The screenshot evidence is saved locally in
`output/react-*.png` (not committed). API regressions cover real extraction/indexing
with controlled models, isolation, invalid paths/origins, settings validation,
concurrent requests and remote cleanup failure. New API checks cover history after a
server-state restart, cross-session history access, replacement rollback, failed-file
recovery, remote individual deletion, cancellation and regeneration. See
`feature-api.log`, `features-regression.log` and frontend test results for local runs.

The existing format/retrieval tests remain applicable. No new claims are made about
live R2R/LM Studio/TabbyAPI servers, Docker deployment or hosted CI. Their independent
verification is unchanged by a UI migration. OCR and arbitrary-document accuracy
remain outside the verified scope.

Implementation references: [React with Vite](https://react.dev/learn/build-a-react-app-from-scratch),
[FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/) and
[streaming responses](https://fastapi.tiangolo.com/advanced/stream-data/).
