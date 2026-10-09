# Contributing

Thank you for considering contributing to DocMind! This guide outlines how to report issues, suggest features, and submit changes.

## Getting Started

1. Fork the repository and create a feature branch.
2. Set up the environment as described in [Setup](setup.md).
3. Make your changes, keeping them focused on a single issue or feature.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) naming conventions: lowercase names separated by underscores.
- Keep indentation consistent with the surrounding code.
- `black` and `ruff` are available in the dev environment:
  ```bash
  pipenv run black .
  pipenv run ruff check . --select E9,F63,F7,F82
  ```
- Keep UI changes small and consistent with the existing Streamlit patterns.

## Testing

Run focused tests while iterating, then the full local suite before submitting:

```bash
pipenv run python -m unittest discover -s tests
pipenv run python -m py_compile main.py components/page_state.py components/tabs/settings.py utils/browser_settings.py utils/ollama.py
```

For a Streamlit smoke test:

```bash
pipenv run streamlit run main.py --server.headless=true --server.port=8520 --server.address=127.0.0.1
curl -s http://127.0.0.1:8520/_stcore/health
```

Stop the smoke-test Streamlit process after checking the health endpoint.

Add or update tests for behavior changes, especially validation, persistence, ingestion safety, and model-selection state.

## Commit Messages

Use descriptive commit messages that clearly explain the purpose of the change and reference the issue it resolves. For example:

```
Fix GitHub repo ingestion failures caused by stale checkouts (#123)
```

## Pull Requests

- Use pull requests for all changes, even small fixes.
- Give the pull request a meaningful title that describes the change.
- Ensure tests pass and the app runs cleanly before submitting.
- Security-sensitive areas to review carefully:
  - File uploads and path handling in `utils/helpers`
  - Website ingestion and URL validation
  - GitHub cloning and subprocess calls
  - Ollama endpoint handling
  - Any code that writes to disk or fetches remote content

## Issue Tracking

- Use the [issue templates](https://github.com/Amaann190/DocMind-AI/issues/new/choose) for bug reports and feature requests.
- Bug reports should include the affected version or commit, operating system, reproduction steps, and relevant console log excerpts.
- Do not include sensitive documents, private repository contents, or credentials in public issues.

## Dependencies

- Dependencies are managed with `Pipfile` / `Pipfile.lock`. Install with `pipenv sync --dev`; regenerate the lockfile deliberately after dependency changes.
- Review dependency updates and test them before merging. This checkout does not establish that automatic dependency merges are enabled.

## License

By contributing to DocMind, you agree that your contributions are licensed under the [GPL-3.0 license](../LICENSE).
