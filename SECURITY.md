# Security Policy

## Reporting a Vulnerability

Please report suspected vulnerabilities through GitHub's private vulnerability reporting for this repository:

https://github.com/Ashita-no-Kaushar/DocMind-AI/security/advisories/new

If private reporting is unavailable, open a [GitHub issue](https://github.com/Ashita-no-Kaushar/DocMind-AI/issues) and avoid including exploit details, private data, credentials, or sensitive local files in the public report.

## Response Expectations

Security reports are reviewed as soon as practical, with an initial response target of 14 days or less. Confirmed medium, high, or critical vulnerabilities are prioritized for a fix and release.

## Supported Versions

The project currently supports the latest released version. Users should upgrade to the newest GitHub release when security fixes are published:

https://github.com/Ashita-no-Kaushar/DocMind-AI/releases

## Scope

Reports are most useful when they include:

- The affected DocMind version or commit.
- The operating system and deployment method.
- Clear reproduction steps.
- The expected and actual security impact.

Do not include sensitive documents, private repository contents, model prompts containing secrets, or local credentials in reports.

## Security Features

DocMind includes guardrails for common ingestion risks:

- Upload size and type validation (see `utils/helpers.py`).
- URL validation and private/loopback IP blocking for website ingestion.
- GitHub repository validation with subprocess isolation and timeouts.
- Ollama endpoint handling with no secrets persisted beyond browser-local storage.
- Hardened Docker deployment: read-only filesystem, dropped capabilities, no new privileges, resource limits.
