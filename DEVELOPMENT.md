# Development

Notes for contributing to PDF Toolbox. All Python modules live inside the `pdf_toolbox` package located in the `src` directory to provide a clear project structure.

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

The configuration uses `language: system` so hooks run in the active virtual environment. Hooks lint, format, type-check, and run tests on every commit, even if you only edit documentation. Test coverage must reach at least 95% for each module (excluding `pdf_toolbox/gui.py`), and the hooks enforce this threshold. Activate the `.venv` before installing or running them:

```bash
pre-commit install
```

To check the entire codebase manually:

```bash
pre-commit run --all-files
```

Run tests with:

```bash
pytest
```

The CI workflow runs `pre-commit run --all-files` and `python -m compileall .` to ensure the codebase passes checks and compiles.

## Release

The release workflow runs only when a version tag (matching `v*`) is pushed. This allows releases to be cut manually instead of on every commit.

To cut a new release:

1. Update the version in `pyproject.toml`.
2. Commit the change.
3. Create and push a matching tag, for example:

   ```bash
   git tag v0.2.62
   git push origin v0.2.62
   ```

The workflow will build the package and publish a GitHub release for that tag.
