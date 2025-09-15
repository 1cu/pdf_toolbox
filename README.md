# PDF Toolbox

![Coverage](./coverage.svg)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Utilities for manipulating PDF files. A Qt-based GUI discovers available functions dynamically and builds forms from their signatures. Launch it with `python -m pdf_toolbox.gui`.

See [CONTRIBUTING](CONTRIBUTING.md) for the contributor workflow and [DEVELOPMENT](DEVELOPMENT.md) for detailed notes, documented linter exceptions, and the release process. Repository-wide rules live in [AGENTS.md](AGENTS.md).

PDF pages can be rasterized to images. When a `max_size_mb` limit is used, JPEG and WebP images lower their quality while PNG or TIFF images boost compression and are only downscaled if necessary, with a warning emitted when resizing occurs.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Optimisation](#optimisation)
- [PPTX Support](#pptx-support)
- [Development](#development)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
python -m pdf_toolbox.gui          # launch the GUI
python -c "from pdf_toolbox.actions.images import pdf_to_images; pdf_to_images('doc.pdf')"  # run an action from the CLI
pre-commit run tests --all-files   # run tests
```

## Configuration

`pdf_toolbox` requires a `pdf_toolbox_config.json` file in the user's platform-specific configuration directory (e.g. `~/.config/pdf_toolbox/` on Linux or `%APPDATA%\\pdf_toolbox\\` on Windows) determined via the `platformdirs` library that specifies the document author and contact email. The Qt GUI warns on startup if the information is missing and lets you set it via the **Author** button. Create the file manually with the following content:

```json
{
  "author": "Your Name",
  "email": "you@example.com"
}
```

Since the file resides outside the repository it remains private and is not tracked by Git.

## Optimisation

`optimise_pdf` (action) supports several quality presets (e.g. `screen`, `ebook`). Each preset also controls the internal compression level by mapping a `pdf_quality` value to the `compression_effort` passed to `fitz.Document.save`. Lower quality values therefore result in higher compression and smaller output files.

After running, the action logs the percentage size change and writes the
optimised file only when the result is smaller. Larger or unchanged outputs are
discarded with an explanatory log message.

See the function docstrings (e.g., via your IDE) for examples and details.
The GUI uses the progress-enabled optimise action for improved responsiveness.

Internationalization: The GUI supports English and German for common UI strings.
Language is auto-detected but can be overridden programmatically using
`pdf_toolbox.i18n.set_language("de")`.

### Adding a New Action

Actions are plain Python callables registered via the `@action` decorator. They
appear in the GUI and are importable for automation. To add one:

```python
from pdf_toolbox.actions import action

@action(category="PDF")
def merge_pdfs(first: str, second: str) -> str:
    """Merge two PDFs into a new file."""
    ...
```

Add a translation key for the function name in `src/pdf_toolbox/locales/en.json`
and `de.json`. Use `tr("key")` for any additional user-facing strings.

Actions can be scripted directly, e.g.:

```bash
python -c "from pdf_toolbox.actions.extract import extract_text; print(extract_text('doc.pdf'))"
```

### Design Notes

- Actions are registered explicitly via an `@action` decorator; only decorated
  callables appear in the GUI.
- Author configuration is cached and missing or malformed files fall back to
  empty strings.
- Page rendering streams directly to disk to keep memory usage low.
- User-supplied paths are validated to prevent directory traversal.

## PPTX Support

The toolbox can manipulate PowerPoint files using pure Python dependencies. Basic actions:

- `extract_pptx_images` – extract embedded images
- `pptx_properties` – write document properties to JSON
- `reorder_pptx` – select and reorder slides

Rendering to images or PDF requires external Office/LibreOffice software and is disabled by default. When a provider is configured, additional actions become available:

- `pptx_to_images` – render slides to images
- `pptx_to_pdf` – render slides to PDF

### PPTX → PDF/Bilder (MS Office Provider)

An experimental provider uses Microsoft PowerPoint via COM automation. It is
**optional** and only works on Windows with PowerPoint installed.

Prerequisites::

```bash
pip install .[pptx-render]
```

Examples:

```bash
python -c "from pdf_toolbox.actions.pptx import pptx_to_pdf; print(pptx_to_pdf('deck.pptx'))"
python -c "from pdf_toolbox.actions.pptx import pptx_to_images; print(pptx_to_images('deck.pptx', img_format='png'))"
```

Basic examples:

```bash
python -c "from pdf_toolbox.actions.pptx import extract_pptx_images; extract_pptx_images('deck.pptx')"
python -c "from pdf_toolbox.actions.pptx import reorder_pptx; reorder_pptx('deck.pptx','2,1')"
```

### Renderer aktivieren (Desktop-Binary)

Prerequisites: Windows and Microsoft PowerPoint installed.

Activate via GUI: `Settings → PPTX Renderer → MS Office (PowerPoint) → Save`.

Alternatively edit the configuration file `${CONFIG_DIR}/pdf_toolbox/pdf_toolbox_config.json`:

```json
{
  "pptx_renderer": "ms_office"
}
```

If the key is absent or empty the renderer remains disabled.

Note: Frozen binaries may lack entry-point metadata. The renderer is then
loaded via an internal registry without loss of functionality.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and workflow guidance and [DEVELOPMENT.md](DEVELOPMENT.md) for developer notes, documented linter exceptions, and the release process.
