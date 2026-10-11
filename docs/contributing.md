# Contributing

Work on the React frontend in `frontend/`, FastAPI endpoints in `backend/`,
and ingestion/retrieval code in `utils/`. Read [AGENTS.md](../AGENTS.md).
Use Python 3.13, Node 22 and the checked-in dependency locks.

Run focused regressions, then:

```bash
pipenv run python -m unittest discover -s tests
pipenv run python -m compileall -q backend utils
pipenv run ruff check . --select E9,F63,F7,F82
pipenv run python eval_harness.py --mock --out output/react-evaluation
cd frontend
npm ci
npm run build
npx playwright install chromium
npm run test:ui
```

Browser tests require the application on port 8765. The optional live Ollama test
uses `DOCMIND_LIVE=1`. Mock evaluation does not measure generated-answer quality.
For deployment edits, build Compose and run `scripts/check_container.py` inside
the container. Do not publish claims that exceed the checks actually run.

Preserve request-state isolation, file/URL guardrails, manual chat names, source
replacement rollback and explicit remote ownership. Never store model credentials
in transcripts or localStorage. Changes to dependencies require updated lockfiles.
