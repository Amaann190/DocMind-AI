# Repair scope and optional work

The agreed repair scope was: make all 25 formats extract text, preserve information
and report failures, repair retrieval/application behavior, and harden/verify deployment.
The final two checkpoints were user workflows/failure recovery and documentation/release
cleanup. See [completed work and verification](completed-work.md).

Implemented areas include the 25 local readers, content preservation, per-file errors,
session-local models/workspaces/caches, retrieval/citation fixes, settings and fallback
chat, provider routing, R2R lifecycle, reset, locked dependencies and container support.
The recorded checks and their limitations are in that report; implementation does not
imply that every third-party server or arbitrary document has been tested.

These are **optional extensions, not additional required phases**:

- OCR for scanned PDFs and images.
- Ingesting documents attached to emails.
- Larger, representative human-reviewed quality and performance datasets.
- Independent security review and authenticated multi-user hosting.
- Live compatibility certification against separately installed LM Studio, TabbyAPI,
  R2R, and AMD/ROCm deployments.
