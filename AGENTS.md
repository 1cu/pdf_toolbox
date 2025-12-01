# Agent Rules

These rules apply to the whole repository. Combine them with any nested
`AGENTS.md` files (`src/pdf_toolbox/AGENTS.md`, `tests/AGENTS.md`, and
`scripts/AGENTS.md`). The most specific file wins.

Read the primary docs before making changes:

- [README](README.md) — project overview and usage.
- [CONTRIBUTING](CONTRIBUTING.md) — contributor workflow and review checklist.
- [DEVELOPMENT](DEVELOPMENT.md) — maintainer notes and tooling details.
- [DEVELOPMENT_EXCEPTIONS](DEVELOPMENT_EXCEPTIONS.md) — generated overview of
  accepted exceptions.
- [CLAUDE.md](CLAUDE.md) — comprehensive guidance for Claude Code instances.

## Set up the environment

- Use Python 3.13 only (version constraint: `>=3.13,<3.15` due to PySide6).
- Before running `pre-commit`, install the system Qt libraries with
  `./scripts/ci/install-qt-headless.sh` (run as root or via `sudo`) so the GUI
  hooks have the dependencies they expect.
- Install Python dependencies with `pip install -e '.[dev]'` or `pdm install`.
- Enable git hooks with `pre-commit install`.
- Run Qt with a native display on desktop machines; do not override
  `QT_QPA_PLATFORM` locally.
- In Linux CI or containerised environments rely on the provided configuration
  (`QT_QPA_PLATFORM=xcb` plus `xvfb-run`). On macOS/Windows CI use the native
  platform. Do not force offscreen plugins.

## Follow the workflow

- Run `pre-commit run --all-files` before committing. Hooks format code (ruff,
  mdformat), lint (ruff, mypy, bandit), run tests (pytest with coverage),
  validate locales, and refresh the exception overview.
- CI runs `pre-commit run --all-files` under Xvfb, so the same lint, format,
  security, metadata, and test hooks run in CI. Keep the pytest hook green
  locally.
- Use the shorter aliases when iterating (`pre-commit run format|lint|tests`).
- Workflows pin third-party actions to immutable commit SHAs and periodically
  update to the latest stable release.
- Keep commits focused and use short imperative subject lines (≤72 characters).

## Meet the quality bar

- Maintain ≥95% coverage overall **and per file**. GUI-only modules listed in
  `pyproject.toml` are the only allowed omissions.
- Tests that run longer than 0.75 seconds must be optimised first; only then may
  they keep `@pytest.mark.slow`. The fast suite and CI will fail any unmarked
  test that crosses the threshold.
- PRs may not introduce unmarked slow tests. Optimise them or mark them with
  `@pytest.mark.slow` before requesting review.
- Run `pre-commit run --all-files` before pushing when you touch code covered
  by the historical slow tests so that the regular test hook catches
  regressions.
- Prefer clear naming and small, testable units. Factor logic out of GUI modules
  when possible.
- Use the shared logging utilities; do not introduce `print` statements for
  logging.
- Keep configuration, locales, and renderer metadata in sync with the docs.

## Document exceptions precisely

- Never add blanket disables such as `# noqa`, `# ruff: noqa`, or `# type: ignore`
  without justification.

- When a single-line exception is unavoidable, add a concise inline comment in
  this format:

  ```python
  import xml.etree.ElementTree as ET  # nosec B405  # pdf-toolbox: stdlib XML parser on trusted coverage file | issue:-
  ```

- Run `python scripts/generate_exception_overview.py` (or rely on the pre-commit
  hook) so `DEVELOPMENT_EXCEPTIONS.md` stays current. Never edit the Markdown file
  manually.

## Review checklist

- [ ] Hooks pass locally (`pre-commit run --all-files`).
- [ ] Coverage still meets the 95% overall/per-file thresholds.
- [ ] No undocumented exceptions or blanket disables appeared.
- [ ] Docs mention `python -m pdf_toolbox.gui` as the GUI entry point.
- [ ] New user-facing strings use locale keys and the i18n helpers.
- [ ] Tests cover both success and failure paths.
- [ ] No unmarked slow tests (optimize or mark with `@pytest.mark.slow`).
