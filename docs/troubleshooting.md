# Troubleshooting

## No models or disabled imports

For Ollama, start the server, check the endpoint (usually `http://localhost:11434`),
and choose Refresh Models. Install both a chat and an embedding model. The recorded
document-answer tests favor `llama3:latest` with `nomic-embed-text:latest` over the
small `qwen2.5:0.5b` model. See [answer quality](answer-quality.md).

For an OpenAI-compatible provider, enter the server's URL and actual chat/embedding
model IDs. Preset placeholders do not install models. R2R needs its own reachable
server and ready uploaded files; local Ollama models are not required for R2R chat.

## Failed or partial imports

The warning names files that could not be read. Answers cover only successfully
loaded files. Install LibreOffice Writer/Impress for DOC/PPT; unlock encrypted files;
scans without text need OCR, which is not included. Upload limits are 10 files,
25 MiB each and 100 MiB total; indexing also limits extracted content.

After fixing the file or connection, choose **Reprocess files**. Settings stays
accessible after an error. That button also applies new embedding/chunk settings.
Repositories accept only `owner/repo` or a repository-root GitHub URL. Website imports
require public HTTPS HTML/text pages and validate every redirect. R2R imports are
limited to Local Files; disable R2R for website/repository imports.

## Settings and reset

Supported settings use browser localStorage, not URL parameters. Invalid saved
values are ignored, and blank Ollama endpoints fall back to the installation default.
API keys and documents are not stored in localStorage. Browsers blocking storage can
still open the app, but preferences may not survive reloads.

Clear Chat retains the index. Reset Project clears the current session's indexes,
uploads, credentials and preferences. If R2R cleanup fails, reset retains the IDs
and original connection so it can retry safely. Restore that server and retry reset.
Closing a browser does not delete remote documents. Lost sessions may need remote
cleanup through the R2R server's own document management.

## Wrong or interrupted answers

Check the recorded source passages. A citation number is not proof of correctness.
An out-of-range source number is flagged, never silently replaced. A failed stream
retains its partial answer and warning; check the server and submit again. After a
retrieval miss, **Ask without documents** requests a general answer separately.

## Logs

Logs go to the launching terminal or `docker compose logs`. The app does not require
a writable project directory or create `docmind.log` by default. Share only relevant
excerpts and remove credentials and private document content from bug reports.

See [setup](setup.md), [usage](usage.md), and [verified release checks](completed-work.md).
