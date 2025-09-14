# Agent Guidelines

This file provides general instructions for all contributors.\
Directory-specific instructions live in `AGENTS.md` files in subdirectories such as `src/pdf_toolbox`, `tests`, and `scripts`.\
When working on a file, apply the rules from this file and any nested `AGENTS.md`.

## Environment

- Install dependencies with `pip install -e '.[dev]'`.
- Install git hooks via `pre-commit install`.
- Export `QT_QPA_PLATFORM=offscreen` when running pre-commit or tests.

## Workflow

- Run `pre-commit run --all-files` before every commit. The hooks format, lint, run tests, and perform security checks.\
  Allow them to finish even if they take a while.
- Use `pre-commit run format|lint|tests` to run subsets when needed.
- If hooks modify files, stage the changes and re-run `pre-commit run --files <file>`.
- Bump the `version` in `pyproject.toml` once per pull request.
- Write descriptive commit messages: short imperative summary (≤72 characters), blank line, then details.

## Quality

- Maintain at least 95% test coverage for every module; modules excluded in
  the coverage configuration in `pyproject.toml` are exempt.
- Use clear, descriptive names for functions and variables.

See the `AGENTS.md` in each subdirectory for additional guidance.\
The most deeply nested instructions take precedence.

______________________________________________________________________

# Linting-Policy: Fix, don’t silence

**Principle**

- Always fix the code first, do not disable the rule.
- Linters help to catch problems early and enforce readability.

**Strictly forbidden (unless covered under “Exceptions” below):**

- `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, `# type: ignore` without justification.
- File- or block-wide disables: `# ruff: noqa`, `flake8: noqa`, `pylint: disable=...`.
- Changes to `pyproject.toml` that weaken/remove rules to make one finding “green”.

**Expected workflow**

1. Understand the warning (read the rule documentation).
1. Simplify/refactor code (e.g. reduce complexity instead of muting `PLR0915`).
1. Strengthen typing or null-handling instead of using `type: ignore`.
1. Update/add tests if refactoring changes behavior.
1. Only if truly unavoidable: follow the exception path below.

**Exceptions (rare cases only)**

A disable is allowed **only if all conditions are met**:

- **Justification in code** (1–2 sentences why the rule does not apply).
- **Minimal scope** (single line, never a file or module).
- **Documentation**:
  - Reference the exception in **`DEVELOPMENT.md`** (or `CONTRIBUTING.md`) with rationale and context.
  - Include an Issue/PR reference if relevant.
- **Follow-up**: If temporary, link to a ticket/plan for eventual removal.

**Examples**

- ✅ Good:

  ```python
  def _scale(img, target):  # cyclomatic complexity < 10
      ...
  ```

````

(Rule satisfied by refactoring.)

* ✅ Rare exception:

  ```python
  result: Any = json.loads(raw)  # noqa: ANN401  # Heterogeneous API payload; adapter planned. Documented in DEVELOPMENT.md.
  ```

* ❌ Bad:

  ```python
  # ruff: noqa
  def build_form(...):
      ...
  ```

  (Global mute without justification.)

**Changes to linter configuration**

* Rules may be modified only after team decision (PR with justification, alternatives, and impact).
* Never lower severity as a workaround.

**PR checklist (enforced in PR template)**

* [ ] All new/changed files lint clean without new disables.
* [ ] No increase in `noqa` / `type: ignore` count.
* [ ] If disable used: justification inline + entry in DEVELOPMENT.md.
* [ ] Tests pass; new tests cover refactoring.

**Review guidelines**

* Reject PRs that silence rules without proper justification and documentation.
* Request refactoring alternatives when complexity, duplication, or typing issues are the cause.

---

## Quick Reference for Common Ruff Rules

* `PLR0915` (too complex): split into helpers, early returns.
* `ANN401` (Any): use precise types or adapters; `Any` only with justification + doc.
* `E/F` (Syntax/Name errors): must be fixed, never ignored.
* `I` (Import sort): sort imports; do not disable.

````

______________________________________________________________________

👉 To make this actionable, add a simple `DEVELOPMENT.md` with a table like:

```markdown
# Development Notes

## Documented Linter Exceptions

| File / Line | Rule | Justification | Linked Issue/PR |
|-------------|------|---------------|-----------------|
| src/pdf_toolbox/foo.py:42 | ANN401 | External API returns arbitrary JSON, adapter planned | #456 |
```
