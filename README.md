# PDF Toolbox

Utilities for manipulating PDF files.

All Python modules live inside the `pdf_toolbox` package located in the
`src` directory to provide a clear project structure.

## Development

### Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Pre-commit hooks
Install the git hooks so formatting, linting, type checks, and tests run automatically on each `git commit`:

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
