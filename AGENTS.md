# AGENTS.md

## Project
DocMind is a React/Vite frontend with a Python FastAPI backend for document RAG.
Use the React worktree for changes; preserve the user's separate original checkout.

- `frontend/src/main.jsx`: website and browser settings.
- `backend/app.py`: API, sessions, imports, chat and source lifecycle.
- `backend/history.py`: SQLite transcripts and titles.
- `utils/`: shared ingestion, model clients and retrieval.
- `tests/` and `frontend/tests/`: backend and browser regressions.

## Setup and verification
Use Python 3.13 and Node 22, the project virtual environment and locked dependencies.

```bash
pipenv sync --dev
cd frontend
npm ci
npm run build
cd ..
pipenv run python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

Windows: `./run.ps1` launches the built app. `run-react.ps1` is an alias.
Run focused tests while iterating, then the retained full suite:

```bash
pipenv run python -m unittest discover -s tests
pipenv run python -m compileall -q backend utils
pipenv run ruff check . --select E9,F63,F7,F82
pipenv run python eval_harness.py --mock --out output/react-evaluation
```

Build the frontend after UI changes and run Playwright against the running API.
Health endpoint: `/api/health`. Stop temporary verification servers afterward.
Docker builds the React frontend and serves it through FastAPI on 8765; verify
`scripts/check_container.py` inside the read-only Compose service after deployment changes.

## Rules
- Prefer rg and apply_patch. Preserve unrelated work.
- Keep API state inside `request_state` contexts; never add a global session fallback.
- Run one backend worker; document state is in memory.
- Browser localStorage holds preferences, not model credentials.
- Model lists must refresh when the endpoint/provider changes.
- Empty endpoint values must not replace the default.
- Normalize GitHub input with `utils.helpers.normalize_github_repo`.
- Preserve upload/path/archive limits, HTTPS/private-network protection and scoped cleanup.
- Never execute uploaded notebooks, macros or spreadsheet formulas.
- Add tests for validation, persistence, ingestion safety and session isolation changes.
