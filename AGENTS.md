# Agent Guidelines

Repository-wide rules for PDF Toolbox. Directory-specific overrides live in
nested `AGENTS.md` files such as `src/pdf_toolbox/AGENTS.md`,
`tests/AGENTS.md`, and `scripts/AGENTS.md`. Apply the guidance from this file
and any more specific one.

See the [README](README.md) for a quick start, [CONTRIBUTING](CONTRIBUTING.md)
for the contributor workflow, and [DEVELOPMENT](DEVELOPMENT.md) for detailed
notes, documented linter and coverage exceptions, and the release process.

## Environment

- Install dependencies with `pip install -e '.[dev]'`.
- Install git hooks via `pre-commit install`.
- Export `QT_QPA_PLATFORM=offscreen` when running pre-commit or tests.

## Workflow

- Run `pre-commit run --all-files` before every commit. Hooks format, lint,
  type-check, run tests, and perform security checks.
- Use `pre-commit run format|lint|tests` to run subsets when needed.
- If hooks modify files, stage the changes and re-run `pre-commit run --files <file>`.
- Bump the `version` in `pyproject.toml` once per pull request.
- Write descriptive commit messages: short imperative summary (≤72 characters), blank line, then details.

## Quality

- Maintain ≥95% test coverage for every module (modules excluded in the
  coverage configuration in `pyproject.toml` are exempt).
- Use clear, descriptive names for functions and variables.

See the `AGENTS.md` in each subdirectory for additional guidance. The most
deeply nested instructions take precedence.

______________________________________________________________________

## Linting Policy: Fix, Don’t Silence

Our rule: **Fix the code instead of silencing linters.**

### Strictly forbidden

- `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, or `# type: ignore` without
  justification.
- File‑ or block‑wide disables such as `# ruff: noqa`, `flake8: noqa`, or
  `pylint: disable=...`.
- Weakening linter settings in `pyproject.toml` to hide a single warning.

### Expected workflow

1. Understand the warning and read the rule documentation.
1. Refactor or strengthen typing instead of disabling.
1. Update or add tests if behavior changes.
1. Only if truly unavoidable, follow the exception process below.

### Exceptions (rare)

A disable is allowed **only if all conditions are met**:

- One‑line justification in code.
- Minimal scope (single line).
- Documented in [DEVELOPMENT.md](DEVELOPMENT.md#documented-exceptions)
  with rationale and Issue/PR reference.
- Temporary? link to a follow‑up ticket.

### Changes to linter configuration

Rules may be modified only after team decision (PR with justification,
alternatives, and impact). Never lower severity as a workaround.

### PR checklist

- [ ] `pre-commit run --all-files` passes.
- [ ] No new linter or coverage disables.
- [ ] Any exception documented in DEVELOPMENT.md.
- [ ] Tests cover the change.

### Review guidelines

Reject PRs that silence rules or exclude coverage without proper justification
and documentation. Request refactoring when complexity, duplication, or typing
issues trigger warnings.

______________________________________________________________________

## Coverage Policy: Test, Don’t Exclude

- Business logic must be testable, even in GUI modules.
- Avoid coverage exclusions (`# pragma: no cover`, `# coverage: ignore`, etc.).
- If unavoidable, limit to a single line, include a brief inline justification,
  and document the exclusion in [DEVELOPMENT.md](DEVELOPMENT.md#documented-exceptions).
- Reviewers should reject PRs with undocumented or unjustified coverage exclusions.

______________________________________________________________________

## Quick Reference for Common Ruff Rules

- `PLR0915` (too complex): split into helpers, early returns.
- `ANN401` (Any): use precise types or adapters; `Any` only with justification + doc.
- `E/F` (Syntax/Name errors): must be fixed, never ignored.
- `I` (Import sort): sort imports; do not disable.
