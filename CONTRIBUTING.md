# Contributing to PDF Toolbox

Thank you for considering contributing! This document explains how to set up your environment, follow our workflow, and meet our quality standards.

See the [README](README.md) for a project overview and quick start, [DEVELOPMENT](DEVELOPMENT.md) for detailed notes, documented linter exceptions, and the release process, and [AGENTS](AGENTS.md) for the enforcement rules.

______________________________________________________________________

## Table of Contents

- [Environment Setup](#environment-setup)
- [Workflow](#workflow)
- [Code Quality](#code-quality)
- [Linting Policy: Fix, Don’t Silence](#linting-policy-fix-dont-silence)
- [Testing](#testing)
- [Pull Requests](#pull-requests)

______________________________________________________________________

## Environment Setup

Create a virtual environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Install pre-commit hooks:

```bash
pre-commit install
```

Run the GUI directly from source:

```bash
python -m pdf_toolbox.gui
```

______________________________________________________________________

## Workflow

- Run `pre-commit run --all-files` before every commit.
- Hooks format, lint, type-check, run tests, and perform security checks.
- Stage modified files and re-run pre-commit until clean.
- Use descriptive commit messages: short imperative summary (≤72 chars), blank line, then details.
- Bump `version` in `pyproject.toml` once per pull request.

______________________________________________________________________

## Code Quality

- Maintain ≥95% coverage for all non-exempt modules.
- Use clear, descriptive names for variables and functions.
- Provide type annotations and meaningful docstrings.
- Keep functions small and focused.

______________________________________________________________________

## Linting Policy: Fix, Don’t Silence

This project follows a strict no-silencing policy (see [AGENTS.md](AGENTS.md)):

- Do **not** add `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, or `# type: ignore` unless absolutely unavoidable.
- Do **not** disable rules globally or change linter config to “make it green”.

If you must add an exception:

1. Add a one-line justification directly in code.
1. Restrict scope to a single line (never file/module-wide).
1. Document the exception in [`DEVELOPMENT.md`](DEVELOPMENT.md#documented-exceptions) under “Documented Exceptions”.
1. Link to the relevant Issue/PR.

Pull requests that violate this policy will be rejected.

______________________________________________________________________

## Testing

- All existing tests must pass.
- Add unit or integration tests for new functionality.
- Cover negative/error cases.
- Run the full test suite with:

```bash
pre-commit run tests --all-files
```

______________________________________________________________________

## Pull Requests

- Use the [PR template](.github/pull_request_template.md).
- Verify the linting checklist is complete.
- Ensure no undocumented linter disables; reviewers will reject PRs that silence rules without entries in [DEVELOPMENT.md](DEVELOPMENT.md#documented-exceptions).
- Document breaking changes and update `README.md` if needed.
- Keep PRs focused: one logical change per PR.

______________________________________________________________________

## Questions and Support

- Use [GitHub Discussions](https://github.com/1cu/pdf_toolbox/discussions) for questions and ideas.
- Report bugs or request features using the provided [issue templates](.github/ISSUE_TEMPLATE/).

______________________________________________________________________

By following these guidelines, you help keep PDF Toolbox reliable, maintainable, and contributor-friendly.
