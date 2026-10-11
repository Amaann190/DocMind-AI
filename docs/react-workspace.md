# DocMind Workspace: React and FastAPI

React/Vite is the project's only web interface. FastAPI serves the production
website and the processing API. The user's separate original checkout is preserved.

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
./run.ps1
```

Open **http://127.0.0.1:8765**. The launcher uses one server for the built React
application and its API.
Use `./run.ps1 -Port 8766` to choose another port.

Docker/Compose builds this React interface and serves it through FastAPI on 8765.
Chat history uses a persistent volume. See [setup](setup.md) for storage and overrides.
Pushing the repository does not host a public website.

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
  DM Sans/Manrope typography bundled locally with the React interface.
- A moon/sun control in the header switches light and dark mode. The first visit
  follows the device theme; an explicit choice is saved locally and applied before
  rendering on later visits. Theme switching also works with browser storage blocked.
- A dedicated conversation view, source library and settings page. The source rail
  gives access to extracted text; answer citations open their retrieved passages.
- File selection and drag-and-drop for all 25 existing supported extensions,
  HTTPS website import, public GitHub import, and an explicitly labeled sample.
- Incremental streamed answers, copy, Word export, answer style and model controls.
- Automatically saved conversations with rename, content/title search, reopen and delete.
  Titles summarize the opening topic after the first answer; manual names are preserved.
  Empty drafts are reused and stay out of saved history until the first message.
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
  code requires an explicit API/evaluation request context; there is no global UI fallback.
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

See [runtime verification](runtime-validation.md) for the current test commands.
The backend regressions cover source lifecycle, history, cancellation, title generation,
session isolation and ingestion safety. Playwright covers the rendered React workflows.
Live model checks must be requested explicitly; mocked checks do not measure answer quality.

Chat names summarize the opening exchange using the selected chat model, with a short
timeout and shortened-message fallback. Naming runs in the background and preserves
manual names. R2R chats use the fallback instead of another configured chat provider.
