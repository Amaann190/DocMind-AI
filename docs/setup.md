# Setup

DocMind uses React/Vite for the website and FastAPI for the Python API.
Install Python 3.13, Node.js 22, Git and Ollama. LibreOffice Writer/Impress enables
DOC/PPT imports; include Calc to run the all-format fixture generator.

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

Open http://127.0.0.1:8765. Windows users can run `./run.ps1` after setup.
Choose another port using `-Port 8766`. The launcher will not terminate a process
already using the selected port. `run-react.ps1` calls the same launcher.

For development, start the API on 8765 and run `npm run dev` from `frontend`.
Open http://localhost:5173. Rebuild the frontend for changes to appear on the
production API URL. Run one API worker.

## Configuration
Choose the provider, endpoint, chat model and embedding model in Settings.
The default Ollama endpoint is http://localhost:11434. Override it with
`DOCMIND_OLLAMA_ENDPOINT`. Set `DOCMIND_LIBREOFFICE` to the converter executable
if automatic detection fails. `DOCMIND_DATA_DIR` chooses the history directory;
the default is the project's `data` directory.

## Docker
```bash
docker compose up --build -d --wait
```
The multi-stage build installs locked dependencies and compiles React. FastAPI
serves the website and API on http://localhost:8765. The default model endpoint is
http://host.docker.internal:11434, reaching Ollama on the host.

The root filesystem is read-only. Temporary extraction/cache paths remain
writable and conversation history is stored in the `docmind-data` volume.
`docker compose down` preserves that volume; `down -v` deletes it.
Override `DOCMIND_PORT` if a local app already uses 8765, and `DOCMIND_CPUS`
if fewer than four CPUs are available to Docker.

```bash
docker compose exec -T docmind python < scripts/check_container.py
```

The container check exercises React assets, API/session storage, Office
conversion and indexing. Model availability and answer quality require separate
checks. GPU access belongs to the Ollama server, not this web container.
