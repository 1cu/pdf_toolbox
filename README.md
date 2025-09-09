# PDF Toolbox

Utilities for manipulating PDF files.

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
hatch run install-hooks  # or: pre-commit install
```

To check the entire codebase manually:

```bash
hatch run precommit  # or: pre-commit run --all-files
```

### Available scripts

The project defines Hatch scripts for common tasks:

```bash
hatch run lint       # Ruff linting
hatch run format     # Ruff formatting
hatch run typecheck  # mypy static checks
hatch run test       # pytest
hatch run build      # byte-compilation
hatch run precommit  # run all pre-commit hooks
hatch run install-hooks  # install git hooks
```

The CI workflow runs `hatch run precommit` and `hatch run build` to ensure the codebase passes checks and compiles.
