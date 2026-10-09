# Security review: retrieval and ingestion

The October 2026 changes address these concrete boundaries:

- Each Streamlit session owns a temporary workspace, upload operations and index caches.
  Model objects are passed explicitly; no shared LlamaIndex model settings or placeholder
  API-key environment overrides remain. New sessions do not reuse another session's cache.
- Reset and failed-import cleanup affect only resources owned by the current session or
  operation. Failed imports invalidate the previous active corpus.
- Upload validation checks actual buffer sizes, rejects duplicate names ignoring case,
  and blocks reserved Windows device names. Office/EPUB archive expansion is checked
  before parsing (100 MB uncompressed, at most 10,000 members).
- Repository names cannot be dot segments. Clone destinations are generated locally;
  filenames cannot choose the destination. Source files must remain inside the selected
  source directory. Git uses a fixed argument list, a timeout, disabled hooks and no
  local-file transport.
- Website ingestion connects to the public IP returned by its validation step, checks
  every redirect, verifies TLS for the original hostname, caps streamed response size,
  and closes connections on all paths. It uses urllib3's
  [custom hostname support](https://urllib3.readthedocs.io/en/stable/advanced-usage.html#custom-sni-hostname)
  without inheriting proxy or netrc credentials.
- Retrieved content is treated as evidence, not instructions. Old corpus history is
  excluded after re-ingestion. Citation text is never fabricated by the application.

These are application boundaries, not an operating-system sandbox or authentication
system. Model endpoints deliberately allow local servers configured by the user.
Document parsers and LibreOffice run with the application's OS permissions; prompt
instructions cannot guarantee a model will resist every hostile passage. Process
crashes can leave temporary files for OS cleanup. The tests exercise the listed
boundaries with synthetic data, including concurrent sessions and blocked redirects;
they do not certify arbitrary model answers or a public multi-user deployment.

Live answer testing observed a model obeying an instruction embedded in a document
despite the system-level guard. A reminder after the quoted passages made that
specific case pass with `llama3:latest`; it does not establish general injection
resistance. See [answer-quality results and limitations](answer-quality.md).

Live HTTPS ingestion was verified on 2026-10-06 against Python.org on Windows and
inside the Linux container, including a real redirect. `example.com` still failed
DNS resolution in this environment, but other public hosts resolved successfully.
TLS hostname parameters, public-address pinning, blocked redirects, response limits
and cleanup also remain covered by deterministic tests.

Regression coverage: `tests/test_session_security_retrieval.py`,
`tests/test_security_controls.py`, `tests/test_ingestion_correctness.py`, and the
25-format checks in `tests/test_document_readers.py`.
