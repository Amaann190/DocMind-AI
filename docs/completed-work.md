# Current implementation

DocMind's supported interface is React/Vite, served by a Python FastAPI API.
The repository contains one web application and one shared processing backend.

Implemented:
- 25 document readers, validated HTTPS/GitHub imports and bounded ingestion.
- Session-isolated hybrid retrieval, model configuration and citation passages.
- Saved conversations, search, topic titles, manual rename, reopen/delete and Word export.
- Individual source controls, replacement rollback, failed-upload recovery and truthful readiness.
- XLS/XLSX sheet names, XLSX formulas/saved results, and ordinary Unicode filenames.
- Streaming, stop/regenerate, light/dark themes, scrollable/collapsible/resizable panels.
- React/FastAPI launchers, production frontend build, Docker assets/API and persistent history volume.

See [verification](runtime-validation.md) for checks and [limitations](todo.md)
for work that remains outside the implemented scope. Historical test counts for
removed UI code are not current React verification results.
