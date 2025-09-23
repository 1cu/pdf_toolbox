# Contribute to PDF Toolbox

Thank you for helping improve PDF Toolbox. Follow this guide to align with the
project’s tooling, coverage policy, and review expectations.

Read these documents before starting:

- [README](README.md) — what the project does and how to use it.
- [DEVELOPMENT](DEVELOPMENT.md) — maintainer notes and deep dives.
- [AGENTS](AGENTS.md) — enforcement rules for contributors and reviewers.

## Prepare your environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
```

Use Python 3.13 or newer. Run Qt with a native display on desktops; in
containers rely on the environment (`QT_QPA_PLATFORM=xcb` with `xvfb-run`)
instead of forcing offscreen plugins.

Launch the GUI from source to verify changes:

```bash
python -m pdf_toolbox.gui
```

## Follow the workflow

- Run `pre-commit run --all-files` before every commit. Hooks format, lint,
  type-check, run pytest with coverage, enforce per-file coverage via
  `scripts/check_coverage.py`, refresh `DEVELOPMENT_EXCEPTIONS.md`, and run
  bandit.
- Iterate with the shorter aliases (`pre-commit run format|lint|tests`).
- Keep commits focused and use short imperative messages (≤72 characters).

## Run tests locally

- Prefer `pre-commit run tests --all-files` so the same arguments as CI are used.
- Maintain ≥95% coverage overall **and** per file. The only exclusions are the
  GUI-only modules listed in `pyproject.toml`.
- Add or update tests for every functional change, including negative paths.

## Document exceptions correctly

When a rule cannot be satisfied, add a single-line justification and capture it
with the generator script:

```python
value = json.loads(payload)  # noqa: S506  # pdf-toolbox: trusted payload from config file | issue:-
```

- Keep the scope to one line; never add file-wide disables.
- Use the `# pdf-toolbox: <reason> | issue:<id or ->` suffix.
- Run `python scripts/generate_exception_overview.py` (or rely on the hook) so
  `DEVELOPMENT_EXCEPTIONS.md` stays updated.

## Submit your pull request

- Complete the PR template checklist. Mention testing commands that ran locally.
- Explain why the change is needed, user impact, and any exception additions or
  removals.
- Link related issues and describe follow-up work when applicable.
- Expect reviews to block merges if coverage drops, hooks fail, or exceptions are
  undocumented.
