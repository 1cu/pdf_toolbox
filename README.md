# PDF Toolbox

Utilities for manipulating PDF files. A Qt-based GUI discovers available
functions dynamically and builds forms from their signatures. Launch it with
`python -m pdf_toolbox.gui`.

The toolbox can also export PPTX presentations to images (JPEG, PNG, or TIFF)
using Microsoft PowerPoint. TIFF exports are lossless for higher-quality
results, and images are organized in a format-specific subdirectory.

All Python modules live inside the `pdf_toolbox` package located in the
`src` directory to provide a clear project structure.

## Configuration

`pdf_toolbox` requires a `pdf_toolbox_config.json` file in
the project directory that specifies the document author and contact email.
The Qt GUI warns on startup if the information is missing and lets you
set it via the **Autor** button. Create the file manually with the
following content:

```json
{
  "author": "Your Name",
  "email": "you@example.com"
}
```

The configuration file is ignored by Git so local preferences remain private.

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
pip install -e '.[dev]'
```

This installs the development dependencies, including the `build` package
used to create distributions. The quotes around `.[dev]` ensure compatibility
across different shells.

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
The configuration uses `language: system` so hooks run in the active virtual
environment. Hooks lint, format, type-check, and run tests on every commit,
even if you only edit documentation. Test coverage must reach at least 80%
for each module (excluding `pdf_toolbox/gui.py`), and the hooks enforce this
threshold. Activate the `.venv` before installing or running them:

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

### Release

The release workflow automatically tags and publishes a release when changes
to `pyproject.toml` are pushed to the `main` branch. The tag is derived from the
`version` field in `pyproject.toml`. If the tag already exists, the workflow
skips the release.

To cut a new release:

1. Update the version in `pyproject.toml`.
2. Commit the change and push to `main`.

The workflow will create the corresponding tag and GitHub release.
