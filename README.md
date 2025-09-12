# PDF Toolbox

Utilities for manipulating PDF files. A Qt-based GUI discovers available functions dynamically and builds forms from their signatures. Launch it with `python -m pdf_toolbox.gui`.

The toolbox can also export PPTX presentations to images (JPEG, PNG, or TIFF) using Microsoft PowerPoint. TIFF exports are lossless for higher-quality results, and images are organized in a format-specific subdirectory.

PDF pages can likewise be rasterized to images. When a `max_size_mb` limit is
used, JPEG and WebP images lower their quality while PNG or TIFF images boost
compression and are only downscaled if necessary, with a warning emitted when
resizing occurs.

## Table of Contents

- [Configuration](#configuration)
- [Optimization](#optimization)
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

## Optimization

`optimize_pdf` supports several quality presets (e.g. `screen`, `ebook`). Each preset now also controls the internal compression level by mapping a `pdf_quality` value to the `compression_effort` passed to `fitz.Document.save`. Lower quality values therefore result in higher compression and smaller output files.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for environment setup, contributing, and release instructions.
