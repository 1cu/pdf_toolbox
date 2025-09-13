# Development

Notes for contributing to PDF Toolbox. All Python modules live inside the `pdf_toolbox` package located in the `src` directory to provide a clear project structure.

GUI is split under `pdf_toolbox/gui/` into `config.py`, `widgets.py`, `worker.py`, and `main_window.py` with a thin facade in `pdf_toolbox/gui/__init__.py`. Headless helpers (`gui/config.py`, `gui/__init__.py`) are covered by tests; pure GUI modules are excluded from coverage in `pyproject.toml`.

The default optimise action is `optimise_pdf` (with optional progress callback). A private helper `_optimise_pdf` contains core logic without progress.

Internationalization: basic English/German translations are provided by `pdf_toolbox.i18n`. Use `i18n.tr()` for UI strings and `i18n.set_language()` to override auto-detection when testing.

## Table of Contents

- [Set up the environment](#set-up-the-environment)
- [Build the distribution](#build-the-distribution)
- [Run the source](#run-the-source)
- [Pre-commit hooks](#pre-commit-hooks)
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

## Pre-commit hooks

The configuration uses `language: system` so hooks run in the active virtual environment. Markdown documentation and YAML configuration files are automatically formatted with `mdformat` and `pretty-format-yaml` (configured with an extra two-space offset and preserved quotes for GitHub Actions compatibility) to avoid introducing a Node.js dependency like Prettier. Hooks lint, format, type-check, and run tests on every commit, even if you only edit documentation. Test coverage must reach at least 95% for each module (excluding `pdf_toolbox/gui.py`), and the hooks enforce this threshold. Ruff applies an extensive rule set, covering bugbear, pyupgrade, naming, builtins, comprehensions, tidy imports, return-value checks, common simplifications, docstring style, security checks, and Pylint-inspired rules. Activate the `.venv` before installing or running them:

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
