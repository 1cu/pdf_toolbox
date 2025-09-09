# PDF Toolbox

Utilities for manipulating PDF files.

All Python modules live inside the `pdf_toolbox` package located in the
`src` directory to provide a clear project structure.

## Optimization

`optimize_pdf` supports several quality presets (e.g. `screen`, `ebook`).
Each preset now also controls the internal compression level by mapping a
`pdf_quality` value to the `compression_effort` passed to
`fitz.Document.save`. Lower quality values therefore result in higher
compression and smaller output files.

## Development

### Set up the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Build the distribution

Create source and wheel distributions in the `dist/` folder:

```bash
python -m build
```

### Run the source

Start the GUI application directly from the source tree:

```bash
python -m pdf_toolbox.gui
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
