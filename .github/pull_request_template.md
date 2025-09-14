# Pull Request

## Description

<!-- What was changed, why, and what is the impact? -->

Fixes: #\<issue_number> (if applicable)

______________________________________________________________________

## Checklist

### Code Quality & Linting (AGENTS.md → “Fix, don’t silence”)

- [ ] All files pass `pre-commit run --all-files`.
- [ ] No new `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, `# type: ignore`, or coverage skips (`# pragma: no cover`, `# coverage: ignore`).
- [ ] If a disable or exclusion was **absolutely necessary**:
  - [ ] Inline justification (1–2 sentences) is present.
  - [ ] Scope is minimal (single line; no file/module-wide disable).
  - [ ] Linked Issue/Ticket reference included.
- [ ] No loosening of linter rules in `pyproject.toml` (unless approved by team in a separate PR).

### Architecture & Maintainability

- [ ] High-complexity functions were refactored (no “mute PLR” shortcuts).
- [ ] Clear, descriptive names; meaningful docstrings and type annotations.
- [ ] Changes align with module structure and conventions.

### Tests

- [ ] All tests pass (`pytest`).
- [ ] New/changed code is covered by unit/integration tests (incl. negative paths).
- [ ] No decrease in coverage; target ≥ 95% for non-exempt modules.

### Security & Stability

- [ ] Path operations validated (no directory traversal; user input sanitized).
- [ ] No new dynamic imports without whitelist/validation.
- [ ] Robust config handling (fallbacks; no hard crashes on missing config).

### Docs

- [ ] Updated `README` / `AGENTS.md` / `CONTRIBUTING.md` as needed.
- [ ] Breaking changes and migrations documented.
- [ ] Examples/usage updated for API/CLI/GUI changes.

______________________________________________________________________

## Reviewer Notes

<!-- Where should reviewers focus? Any open questions or TODOs? -->

## PR Type

- [ ] Bugfix
- [ ] Feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Build/CI
- [ ] Other
