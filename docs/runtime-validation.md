# Deployment and runtime reliability

Validated on Windows and in the Linux Docker container on 2026-10-06.

## Changes

- Docker builds this checkout using the checked dependency lock. Its runtime includes
  Git and LibreOffice, uses a Python health check, and copies only application files.
- Compose runs without a GPU requirement, binds the UI to loopback, and supplies a
  host-reachable Ollama default. The non-root user owns its temporary cache directory.
- Logging uses stdout by default, including on a read-only filesystem. An unwritable
  explicitly requested log file no longer prevents startup.
- Model discovery and validation have a five-second timeout per network operation.
  Model generation retains its longer timeout.
- The Windows launcher selects the project environment, works from another directory,
  and reports occupied ports without stopping other apps or deleting files.
- CI now installs the locked dependencies and includes a container health check plus
  application-rendering check under the Compose read-only/non-root restrictions.

## Verification

- All 155 unit tests passed against the locked dependencies, including real fixtures
  for all 25 document extensions and the new runtime tests.
- Compile checks, Ruff, dependency consistency, and the lock hash check passed.
- Both Compose entry points passed configuration validation.
- Streamlit health check passed. The Windows launcher also passed a real health check
  when started outside the project directory. Test servers were stopped afterward.

## Deployment and integration verification completed

- Built `docmind:local` from the locked dependencies on Linux (Python 3.13).
- Started an isolated `docmind-validation` Compose project on loopback port 8521.
  The service became healthy with the configured non-root user and read-only root.
- Ran `scripts/check_container.py` in that service: the full app rendered with an
  unavailable model server; real DOC/DOCX/PPT/PPTX conversion and extraction, bundled
  tokenization, indexing, index persistence/reload, retrieval, cache permissions, and
  temporary workspace cleanup all passed without a model server.
- Repeated that integration script in a read-only container with `--network none`;
  all checks passed with networking completely disabled (mock embeddings).
- All 25 real synthetic format fixtures passed extraction inside the Linux image.
- Live Python.org HTTPS pages passed extraction on both Windows and Linux. A website
  was embedded through the installed host `nomic-embed-text:latest` model and retrieved
  successfully from its index on both platforms.
- Public GitHub repository validation and isolated cloning passed on both platforms.
- The default Docker endpoint `http://host.docker.internal:11434` reached the installed
  Ollama models. Live chat generation and a real HTTPS redirect passed. The first
  redirect attempt hit a five-second CDN connection timeout; a fresh attempt passed.
- The Windows regression suite still passed all 155 tests; compile and Ruff checks passed.
- The temporary Compose service/network were removed after verification.

The same offline container integration script now runs in the CI container job.
That script was executed locally against the built image; a hosted GitHub Actions run
has not been triggered or claimed. These are integration checks, not an answer-quality
benchmark or a claim that arbitrary documents always produce correct answers.

## Docker Desktop recovery

Docker initially failed before starting its Linux engine because Windows could not
access stale `dockerInference` and `engine.sock` socket entries. With Docker stopped,
the affected directories were checked to contain only zero-byte runtime sockets,
moved aside, and recreated. Docker then started successfully. No factory reset,
image/volume pruning, or deletion of container data was performed.

The original runtime entries remain under `%LOCALAPPDATA%` in these backup directories:

- `Docker/run.docmind-backup-20261006`
- `Docker/run.docmind-backup-20261006-2`
- `docker-secrets-engine.docmind-backup-20261006-2`

This recovery addressed the observed local failure; it does not establish that Docker's
underlying Windows socket issue cannot recur. Similar failures are reported in the
[Docker issue tracker](https://github.com/docker/desktop-feedback/issues/625).

See [setup instructions](setup.md) for local and container commands.
