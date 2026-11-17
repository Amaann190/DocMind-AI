# Known limitations and possible follow-ups

- OCR for scans and image-only content is not implemented.
- Email attachment extraction is not implemented.
- Spreadsheet formulas are not calculated by DocMind.
- Live answer accuracy depends on model, prompt and document content.
- Sources are restored after a backend restart only when the user opts in; the saved copy is not encrypted.
- Workspaces and indexes live in one process, so the API must run with a single worker.
- Remote R2R ownership is tracked in the active process; clean up remote sources before shutdown.
- Public hosting would require authentication and a different persistent session architecture.

These are limitations, not additional mandatory project phases.
