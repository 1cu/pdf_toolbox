# Development

Notes for contributing to PDF Toolbox. All Python modules live inside the `pdf_toolbox` package located in the `src` directory to provide a clear project structure.

For a project overview and quick start, see the [README](README.md). The main contributor workflow is documented in [CONTRIBUTING](CONTRIBUTING.md). Repository-wide rules are enforced via [AGENTS.md](AGENTS.md).

GUI is split under `pdf_toolbox/gui/` into `config.py`, `widgets.py`, `worker.py`, and `main_window.py` with a thin facade in `pdf_toolbox/gui/__init__.py`. Headless helpers (`gui/config.py`, `gui/__init__.py`) are covered by tests; pure GUI modules are excluded from coverage in `pyproject.toml`.

Internationalization: basic English/German translations are provided by `pdf_toolbox.i18n`. Use `i18n.tr()` for UI strings and `i18n.set_language()` to override auto-detection when testing.

## Table of Contents

- [Set up the environment](#set-up-the-environment)
- [Build the distribution](#build-the-distribution)
- [Run the source](#run-the-source)
- [Pre-commit hooks](#pre-commit-hooks)
- [Linting Policy: Fix, Don’t Silence](#linting-policy-fix-dont-silence)
- [Release](#release)

## Set up the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

This installs the development dependencies, including the `build` package used to create distributions. The quotes around `.[dev]` ensure compatibility across different shells.

## Build the distribution

Create source and wheel distributions in the `dist/` folder:

```bash
python -m build
```

## Run the source

Start the GUI application directly from the source tree:

```bash
python -m pdf_toolbox.gui
```

## PPTX Renderer Providers

PPTX rendering (slides to images or PDF) uses a provider interface defined in
`pdf_toolbox.renderers.pptx`. Third-party renderers can register an entry
point in the `pdf_toolbox.pptx_renderers` group and implement
`BasePptxRenderer`. Without such a provider the default `NullRenderer`
raises a translated `NotImplementedError`.

## Pre-commit hooks

The configuration uses `language: system` so hooks run in the active virtual environment. Markdown documentation and YAML configuration files are automatically formatted with `mdformat` and `pretty-format-yaml` (configured with an extra two-space offset and preserved quotes for GitHub Actions compatibility) to avoid introducing a Node.js dependency like Prettier. Hooks lint, format, type-check, and run tests on every commit, even if you only edit documentation. Test coverage must reach at least 95% for each module; modules excluded by the coverage configuration in `pyproject.toml` are exempt, and the hooks enforce this threshold. Ruff applies an extensive rule set, covering bugbear, pyupgrade, naming, builtins, comprehensions, tidy imports, return-value checks, common simplifications, docstring style, security checks, and Pylint-inspired rules. Activate the `.venv` before installing or running them:

```bash
pre-commit install
```

To check the entire codebase manually:

```bash
pre-commit run --all-files
```

`pre-commit run --all-files` executes tests, so no separate `pytest` step is required. The CI workflow runs `pre-commit run --all-files` and `python -m compileall .` to ensure the codebase passes checks and compiles.

Hooks share aliases so related groups can run independently:

```bash
pre-commit run format --all-files  # formatters
pre-commit run lint --all-files    # linters and static analysis
pre-commit run tests --all-files   # test suite
```

Bandit performs static security checks during pre-commit. Dependency
vulnerability auditing is omitted because the project is not published on
PyPI.

## Linting Policy: Fix, Don’t Silence

PDF Toolbox follows a **“Fix, Don’t Silence”** linting policy (see [AGENTS.md](AGENTS.md) and [CONTRIBUTING](CONTRIBUTING.md)):

- Warnings should be fixed through refactoring, not disabled.
- No new `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, or `# type: ignore` are allowed unless justified.

If an exception is truly unavoidable:

1. Add a one-line justification in code (1–2 sentences).
1. Restrict the scope to a single line (never a file or module).
1. Run `scripts/generate_exception_overview.py` via pre-commit to update `DEVELOPMENT_EXCEPTIONS.md`.
1. Link the related Issue/PR for visibility.

### Documented Exceptions

See [DEVELOPMENT_EXCEPTIONS.md](DEVELOPMENT_EXCEPTIONS.md). The file is generated; never edit it manually. Reviewers will reject PRs that introduce undocumented disables.

## Release

The release workflow runs only when a version tag (matching `v*`) is pushed. This allows releases to be cut manually instead of on every commit.

To cut a new release:

1. Update the version in `pyproject.toml`.
1. Commit the change.
1. Create and push a matching tag, for example:

```bash
git tag v0.2.62
git push origin v0.2.62
```

The workflow will build the package and publish a GitHub release for that tag.

```
```
