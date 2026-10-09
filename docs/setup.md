# Setup

Before you get started with DocMind, ensure you have:

- A local [Ollama](https://github.com/ollama/ollama/) instance
- At least one chat-capable model available in Ollama
  - `llama3:latest` passed the recorded document-answer checks; `qwen2.5:0.5b` was unreliable on those same checks. See [the comparison](answer-quality.md).
- At least one embedding-capable model available in Ollama
  - `nomic-embed-text:latest` is the tested default Ollama embedding model
- Python 3.12-3.13
- LibreOffice for legacy `.doc` and `.ppt` files (conversion runs locally)

DocMind is tested on Windows and Linux. Windows Subsystem for Linux (WSL) is not currently tested.

## Local

Install LibreOffice before using legacy Office files. On Windows:

```powershell
winget install --id TheDocumentFoundation.LibreOffice --exact
```

On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install libreoffice-writer libreoffice-impress
```

DocMind discovers standard Windows installations and `soffice`/`libreoffice` on `PATH`.
For a custom installation, set `DOCMIND_LIBREOFFICE` to the full path of its executable.
On Windows, prefer `soffice.com` in LibreOffice's `program` directory.

Install or refresh the Python dependencies (including Excel, PowerPoint, and Outlook readers):

```bash
pip install pipenv
pipenv sync
pipenv run streamlit run main.py
```

The default Ollama endpoint is `http://localhost:11434`. Set `DOCMIND_OLLAMA_ENDPOINT`
to override the installation default, or change it in Settings. Saved browser settings
take precedence. The app refreshes model lists for the configured endpoint.

On Windows, `./run.ps1` also starts the project environment from any working directory.
Use `./run.ps1 -Port 8502` if port 8501 is occupied. The launcher leaves existing
processes and files alone. Start Ollama separately; the UI can open while it is offline.

For development use `pipenv sync --dev`. After intentionally changing dependencies,
run `pipenv lock`, test the resolved environment, and commit `Pipfile.lock`.

To verify extraction for all 25 extensions without Ollama or model downloads:

```bash
pipenv run python -m unittest discover -s tests -p test_document_readers.py -v
```

The checks generate real sample files, including legacy Office containers. On Linux,
install `libreoffice-calc` as well to generate the XLS test sample; reading XLS in the
application uses `xlrd` and does not require Calc.

Useful Ollama commands:

```bash
ollama pull llama3:latest
ollama pull nomic-embed-text:latest
ollama list
```

## Docker

```bash
docker compose up --build -d --wait
docker compose logs -f
```

Open `http://localhost:8501`. Compose builds the current checkout with locked Python
dependencies, Git, and LibreOffice. It runs as a non-root user with a read-only root,
writable temporary directories, resource limits, and console logs. Build inputs exclude
local documents, caches, environment files, and Streamlit secrets. Internet access is
needed for the initial image/dependency build.

The UI does not need GPU access; run Ollama with the appropriate GPU support separately.
`docker-compose.yml-rocm` remains a compatibility entry point for the same service
(requires Docker Compose 2.20 or newer).

Compose defaults to `http://host.docker.internal:11434` and includes the Linux host
mapping. Ollama must listen on an interface reachable from Docker; a host service bound
only to loopback may not be reachable. Restrict access with the host firewall if changing
Ollama's bind address. Set `DOCMIND_OLLAMA_ENDPOINT` before launching Compose to use
another server. Existing browser settings may need updating in Settings.

Set `DOCMIND_PORT` to change the local UI port. The UI binds to loopback by default;
authentication is not included. Session documents and indexes are temporary and are
lost when the container is stopped. Stop it with `docker compose down`.

The health check confirms the Streamlit server is responding; it does not guarantee
that Ollama is reachable or that the selected models have been downloaded.

For a deeper check of the read-only container (no model server needed), run:

```bash
docker compose exec -T docmind python < scripts/check_container.py
```

PowerShell equivalent:

```powershell
Get-Content scripts/check_container.py -Raw | docker compose exec -T docmind python -
```

This checks app rendering, Office conversion, indexing, cache permissions, and cleanup.
See [verified deployment results](runtime-validation.md) for the latest checks and limits.
