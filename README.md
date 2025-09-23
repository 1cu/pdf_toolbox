# PDF Toolbox

[![coverage](https://1cu.github.io/pdf_toolbox/badges/coverage.svg)](https://1cu.github.io/pdf_toolbox/)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/1cu/pdf_toolbox?utm_source=oss&utm_medium=github&utm_campaign=1cu%2Fpdf_toolbox&labelColor=171717&color=FF570A&label=CodeRabbit+Reviews)](https://coderabbit.ai)

**PDF Toolbox** is a Python 3.13+ application for turning everyday PDF and PPTX housekeeping into a repeatable workflow. Launch the Qt-powered GUI to work interactively, call the same actions from the `pdf-toolbox` command, or automate them from your own scripts.

## Why use PDF Toolbox?

- **Do more with PDFs:** merge, split, rasterise, and extract assets in bulk.
- **Bring PPTX decks along:** render slides to images with pluggable renderers and export helper metadata.
- **Work visually or headless:** the GUI discovers registered actions and builds forms on the fly, while the CLI exposes the same registry for automation.
- **Stay within Miro limits:** ship-ready exports keep vectors sharp while respecting Miro’s 30 MB / 32 MP / 8192×4096 requirements.
- **Extend without forking:** register a new `@action` callable under `pdf_toolbox.actions` and it appears instantly in the GUI, CLI, and Python API.

## Installation

PDF Toolbox is not available on PyPI. Grab a release build from the
[GitHub releases page](https://github.com/1cu/pdf_toolbox/releases) and choose
the option that matches how you plan to run the tool.

### Download a desktop bundle

- **Windows:** download `pdf_toolbox-<version>-windows.zip`, extract it, and run
  `pdf_toolbox-<version>.exe`. The bundle contains everything the GUI needs,
  including the Qt libraries.
- **macOS:** download `pdf_toolbox-<version>-macos.zip`, unzip it, and drag the
  `pdf_toolbox-<version>.app` bundle into `/Applications` (or any other folder
  you prefer). Launch it like any other unsigned app—macOS may prompt you to
  confirm the first run.

### Install the Python package

Download the `pdf_toolbox-<version>-py3-none-any.whl` wheel from the same
release and install it into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install /path/to/pdf_toolbox-<version>-py3-none-any.whl
```

Use this path when you want to script actions, run the CLI, or embed the
library into your own automation.

### Develop from source

```bash
git clone https://github.com/1cu/pdf_toolbox.git
cd pdf_toolbox
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install the development extras as well (`pip install -e '.[dev]'`) if you plan
to run the project’s test and lint tooling locally.

### Optional renderer dependencies

Install the supporting libraries that each PPTX renderer requires:

- **Microsoft PowerPoint automation (`ms_office`):**
  `pip install pywin32` (Windows only, requires Microsoft PowerPoint).
- **HTTP bridge (`http_office`):** `pip install requests`.

When working from the source tree you can install these dependencies via the
extras: `pip install '.[pptx-render]'` and `pip install '.[pptx_http]'`.

## Quick start

### Launch the GUI

```bash
python -m pdf_toolbox.gui
```

The window lists every available action, groups them by category, and builds a form from each action’s type hints and default values. Configure options, click **Run**, and monitor progress straight from the log panel.

### Automate from the command line

The `pdf-toolbox` console script exposes the same registry:

```bash
pdf-toolbox list                       # show available actions
pdf-toolbox describe extract_range     # inspect parameters
pdf-toolbox run extract_range --input-pdf in.pdf --pages 1-3
```

### Call actions from Python

```python
from pdf_toolbox.actions.pdf_images import pdf_to_images

pdf_to_images("slides.pdf", max_size_mb=20)
```

Every registered `@action` is importable, so you can wire the building blocks into scheduled jobs or bespoke automation without touching the GUI.

## Configure defaults

PDF Toolbox stores user preferences in `pdf_toolbox_config.json` inside the platform-specific directory returned by `platformdirs` (for example `~/.config/pdf_toolbox/` on Linux or `%APPDATA%\pdf_toolbox\` on Windows). Create the file manually or via the GUI to set your author metadata and pick a PPTX renderer:

```json
{
  "author": "Your Name",
  "email": "you@example.com",
  "pptx_renderer": "ms_office"
}
```

The GUI highlights missing metadata at startup and lets you update the file on the fly.

## Choose a PPTX renderer

Renderer plugins register under the `pdf_toolbox.pptx_renderers` entry point group. Select one by setting `pptx_renderer` in `pdf_toolbox_config.json`:

- `auto` (default) prefers local providers and falls back to installed plugins.
- `none` disables rendering and shows guidance in the GUI.
- `ms_office` uses Microsoft PowerPoint via COM on Windows (requires the `pptx-render` extra).
- `http_office` sends work to an HTTP-capable Office renderer such as Stirling or Gotenberg (requires the `pptx_http` extra).
- `lightweight` activates the built-in stub renderer for smoke testing.

## Export profiles and Miro support

Select the **Miro (optimised for Miro/Boards)** export profile to produce one image per slide while staying inside Miro’s upload limits. Vector slides render as crisp SVG with fonts converted to paths; raster-heavy slides use an adaptive pipeline that balances DPI against file size. Enable the debug manifest option to generate `miro_export.json` with per-page metadata and warnings.

## Localise the interface

PDF Toolbox ships with English and German locales stored in `src/pdf_toolbox/locales/en.json` and `de.json`. The application auto-detects the system language, and the helper API lets scripts override it:

```python
from pdf_toolbox.i18n import label, set_language, tr

set_language("de")
label("actions")
tr("field_cannot_be_empty", field="Password")
```

Add new keys to both locale files when extending the UI so every string stays translatable.

## Troubleshooting Qt on Linux containers

Missing Qt dependencies usually surface as `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, `This application failed to start because no Qt platform plugin could be initialized`, or loader errors such as `libEGL.so.1: cannot open shared object file`. Install the CI dependency bundle and rerun the command under Xvfb:

```bash
sudo apt-get update
sudo apt-get install -y \
  xvfb \
  libxkbcommon-x11-0 \
  libxcb-cursor0 \
  libxcb-icccm4 \
  libxcb-keysyms1 \
  libxcb-shape0 \
  libegl1 \
  libgl1

QT_QPA_PLATFORM=xcb xvfb-run -s "-screen 0 1920x1080x24" pdf-toolbox list
```

## License

PDF Toolbox is distributed under the terms of the [MIT License](LICENSE).

## Continue exploring

- [CONTRIBUTING](CONTRIBUTING.md) — learn how to propose changes.
- [DEVELOPMENT](DEVELOPMENT.md) — dive into architecture and maintainer notes.
- [AGENTS](AGENTS.md) — review the automation and policy rules for this repository.
