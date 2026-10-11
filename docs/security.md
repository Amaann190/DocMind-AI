# Security boundaries

DocMind is a local React/FastAPI application. Run one API worker on loopback.
The cookie/header/origin checks isolate local browser workspaces; they do not
provide user authentication for public hosting.

- Each API session owns its models, document state, lock and temporary directory.
- Request context is explicit; processing outside a context fails.
- Upload validation limits names, types, file size, total retained bytes and archive expansion.
- Unicode and ordinary punctuation in filenames are allowed; traversal, device names,
  path separators, control characters and reserved filesystem characters are rejected.
- HTTPS imports reject private/loopback addresses and pin the validated connection address.
- GitHub imports validate owner/repository names and isolate subprocesses and clones.
- Notebook cells and workbook formulas are read as data, never executed.
- LibreOffice conversion uses isolated profiles with macros disabled.
- R2R queries and deletion use owned document IDs; failed cleanup blocks further queries.

SQLite stores transcript text, titles and citation passages. Raw uploads and model
credentials are not stored there. Browser preferences exclude credentials.
Documents go to the configured model/server; using Ollama does not imply that
an arbitrary configured endpoint is on this computer.

Docker uses a non-root account, read-only application files, dropped capabilities,
resource limits, temporary writable caches and a dedicated conversation-history volume.
Container ports bind to localhost by default. Removing the volume removes history.

Report vulnerabilities using [the repository security policy](../SECURITY.md).
