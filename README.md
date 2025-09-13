# PDF Toolbox

![Coverage](./coverage.svg)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Utilities for manipulating PDF files. A Qt-based GUI discovers available functions dynamically and builds forms from their signatures. Launch it with `python -m pdf_toolbox.gui`.

The toolbox can also export PPTX presentations to images (JPEG, PNG, or TIFF) using Microsoft PowerPoint. TIFF exports are lossless for higher-quality results, and images are organized in a format-specific subdirectory.

PDF pages can likewise be rasterized to images. When a `max_size_mb` limit is
used, JPEG and WebP images lower their quality while PNG or TIFF images boost
compression and are only downscaled if necessary, with a warning emitted when
resizing occurs.

## Table of Contents

- [Configuration](#configuration)
- [Optimisation](#optimisation)
- [Development](#development)

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

After running, the action logs the optimised PDF path and the percentage size change.

See the function docstrings (e.g., via your IDE) for examples and details.
The GUI uses the progress-enabled optimise action for improved responsiveness.

Internationalization: The GUI supports English and German for common UI strings.
Language is auto-detected but can be overridden programmatically using
`pdf_toolbox.i18n.set_language("de")`.

### Design Notes

- Actions are registered explicitly via an `@action` decorator; only decorated
  callables appear in the GUI.
- Author configuration is cached and missing or malformed files fall back to
  empty strings.
- Page rendering streams directly to disk to keep memory usage low.
- User-supplied paths are validated to prevent directory traversal.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for environment setup, contributing, and release instructions.
