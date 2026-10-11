# Runtime verification

Use the current React/FastAPI checkout and its project environment.

```bash
pipenv verify
pipenv run python -m unittest discover -s tests
pipenv run python -m compileall -q backend utils
pipenv run ruff check . --select E9,F63,F7,F82
pipenv run python eval_harness.py --mock --out output/react-evaluation
```

Build the website with `npm ci` and `npm run build` in `frontend`.
Start the API on port 8765, then run `npm run test:ui`. Set `DOCMIND_LIVE=1`
to include the optional live Ollama upload/chat/source workflow.

The all-format tests generate real fixtures, including legacy Office containers.
LibreOffice Writer, Impress and Calc are required for those fixture checks.
Mock model tests verify ingestion, source lifecycle, state, security and retrieval
controls; they do not establish live answer accuracy.

For a container check:
```bash
docker compose up --build -d --wait
docker compose exec -T docmind python < scripts/check_container.py
docker compose down
```

This exercises built React assets, health/session API, persistent database permissions,
Office conversion, index persistence and retrieval under a read-only filesystem.
Keep local test outputs under `output/`; report actual executed and skipped checks
when handing off changes.
