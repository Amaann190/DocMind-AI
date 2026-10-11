# Troubleshooting

- **Website unavailable:** start `./run.ps1` or the FastAPI command in [setup](setup.md).
  Check http://127.0.0.1:8765/api/health. Build `frontend/dist` first.
- **Port occupied:** use `./run.ps1 -Port 8766` or set `DOCMIND_PORT` for Compose.
- **UI changes missing:** run `npm run build` in `frontend` and refresh.
  Restart the Python server after backend changes.
- **Models missing:** verify Ollama is running and the Settings endpoint/model names match.
  Inside Docker, localhost refers to the container; use the configured host endpoint.
- **A file needs attention:** open its source preview for the error, retry, or replace it.
  Corrupt, encrypted, empty and image-only documents can fail even when their extension is supported.
- **DOC/PPT conversion fails:** install LibreOffice Writer/Impress or set
  `DOCMIND_LIBREOFFICE` to its executable.
- **Spreadsheet formula result unavailable:** recalculate and save in Excel or LibreOffice.
  XLSX formula text is retained; DocMind does not evaluate it.
- **Sources missing after restart:** source bytes/indexes are session memory. Upload them again.
  Saved transcripts do not restore old source collections.
- **Missing chat title:** a shortened first message is the fallback if naming is unavailable.
  Manual names are never automatically overwritten.
- **Remote cleanup fails:** restore the R2R server/credentials used to upload the files and retry.
- **Docker CPU error:** set `DOCMIND_CPUS=2` when Docker has only two CPUs available.

For reproducible bugs, include your launch method, file extension, visible error
and model/provider. Do not attach private files or credentials to public issues.
