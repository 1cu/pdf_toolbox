# Agent Guidelines

This file provides general instructions for all contributors. Directory-specific instructions live in `AGENTS.md` files in subdirectories such as `src/pdf_toolbox`, `tests`, and `scripts`. When working on a file, apply the rules from this file and any nested `AGENTS.md`.

## Environment

- Install dependencies with `pip install -e '.[dev]'`.
- Install git hooks via `pre-commit install`.
- Export `QT_QPA_PLATFORM=offscreen` when running pre-commit or tests.

## Workflow

- Run `pre-commit run --all-files` before every commit. The hooks format, lint, run tests, and perform security checks. Allow them to finish even if they take a while.
- Use `pre-commit run format|lint|tests` to run subsets when needed.
- If hooks modify files, stage the changes and re-run `pre-commit run --files <file>`.
- Bump the `version` in `pyproject.toml` once per pull request.
- Write descriptive commit messages: short imperative summary (≤72 characters), blank line, then details.

## Quality

- Maintain at least 95% test coverage for every module; modules excluded in
  the coverage configuration in `pyproject.toml` are exempt.
- Use clear, descriptive names for functions and variables.

See the `AGENTS.md` in each subdirectory for additional guidance. The most deeply nested instructions take precedence.
