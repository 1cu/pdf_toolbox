# PDF Toolbox

[![coverage](https://1cu.github.io/pdf_toolbox/badges/coverage.svg)](https://1cu.github.io/pdf_toolbox/)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/1cu/pdf_toolbox?utm_source=oss&utm_medium=github&utm_campaign=1cu%2Fpdf_toolbox&labelColor=171717&color=FF570A&label=CodeRabbit+Reviews)](https://coderabbit.ai)

PDF Toolbox is a Python 3.13+ toolkit for PDF and PPTX automation. A Qt GUI
(entry point `src/pdf_toolbox/gui/__main__.py`) discovers functions registered
with the `@action` decorator and builds forms from their signatures. You can run
those same actions from the command line or import them in scripts.

## Learn what it does

- Manage PDFs: merge, split, rasterise, and export assets.
- Operate on PPTX files: render with an optional provider.
- Use the Miro export profile to create slide images that respect Miro’s size
  limits while keeping vector pages crisp.
- Extend the GUI by adding new `@action`-decorated callables in
  `pdf_toolbox.actions`. The GUI updates automatically.

## Start quickly

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
python -m pdf_toolbox.gui          # launch the Qt GUI
pre-commit run tests --all-files   # run pytest with coverage on a desktop session
```

## Run an action from Python

Any registered action is available from the CLI or your own scripts:

```bash
python -c "from pdf_toolbox.actions.pdf_images import pdf_to_images; pdf_to_images('doc.pdf', max_size_mb=20)"
```

## Configure the app

Configuration lives in `pdf_toolbox_config.json` inside the platform-specific
config directory returned by `platformdirs` (for example `~/.config/pdf_toolbox/`
on Linux or `%APPDATA%\pdf_toolbox\` on Windows). Create the file manually to
set author metadata and optionally choose a PPTX renderer:

```json
{
  "author": "Your Name",
  "email": "you@example.com",
  "pptx_renderer": "ms_office"
}
```

Set `pptx_renderer` to control how PPTX files render:

- `auto` (default): prefer local providers, fall back to registered plugins.
- `none`: disable rendering and surface the helper banner in the GUI.
- `ms_office`: automate Microsoft PowerPoint via COM on Windows.
- `http_office`: delegate rendering to an HTTP-capable Office deployment such as
  Stirling or Gotenberg.
- `lightweight`: use the built-in stub provider for smoke tests.

The Qt GUI surfaces missing metadata at startup and lets you update the config.

## Select a PPTX renderer

The renderer plugin system loads implementations registered under the
`pdf_toolbox.pptx_renderers` entry point group. The default `NullRenderer`
explains that rendering is unavailable. On Windows, the optional
`ms_office` provider automates Microsoft PowerPoint via COM once you install the
`pptx-render` extra and set `"pptx_renderer": "ms_office"` in the config file.
Future providers plug into the same interface.

## Internationalise the UI

Locale files in `src/pdf_toolbox/locales/{en,de}.json` map JSON keys such as
`actions`, `select_file`, `field_cannot_be_empty`, `input_pdf`, `out_dir`, and
`max_size_mb` to translated strings. Use the helper API:

```python
from pdf_toolbox.i18n import label, set_language, tr

set_language("de")          # override auto-detected language during tests
label("actions")            # look up a label by key
tr("field_cannot_be_empty", field="Password")
```

Add keys to both locale files when you introduce new user-facing strings and
wire them through the GUI instead of hard-coding text.

## Understand the action framework

Register new callables with `@action(category="PDF")`. The decorator captures
metadata, exposes the function under `pdf_toolbox.actions`, and makes it
available in the GUI. The GUI inspects the function signature to build widgets
for typed parameters and handles validation.

## Export for Miro

Choose the “Miro (optimised for Miro/Boards)” profile in the GUI to create
per-page exports that respect Miro’s 30 MB / 32 MP / 8192×4096 limits. Vector
pages render as SVG with fonts converted to paths; raster-heavy slides use an
adaptive pipeline that keeps DPI high while staying within limits. The export
writes `miro_export.json` with per-page metadata and warnings.

## Development quick facts

- Target Python 3.13 or newer; CI and tooling currently run on 3.13.
- Install dependencies with `pip install -e '.[dev]'` and enable hooks via
  `pre-commit install`.
- Pre-commit runs ruff format (Black-compatible formatting), ruff linting,
  mypy, bandit, locale checks, pytest with coverage, and per-file coverage
  enforcement.
- Maintain ≥95% coverage overall **and per file**. Exceptions must be justified
  inline and appear in `DEVELOPMENT_EXCEPTIONS.md` via
  `scripts/generate_exception_overview.py`.
- Use the shared logger utilities for diagnostics; do not use `print` for
  logging.

## GUI test policy

- **Desktop developers (Linux, macOS, Windows):** run Qt with a real display.
  Execute the fast suite with `pre-commit run tests --all-files` and avoid
  `xvfb-run` or other headless flags.

- **CI jobs and coding agents/containers (Linux):** install the X11/EGL
  libraries that the Qt xcb plugin requires, export `QT_QPA_PLATFORM=xcb`, and
  drive the suite through a virtual display:

  ```bash
  xvfb-run -s "-screen 0 1920x1080x24" pre-commit run --all-files
  ```

- **Tests and fixtures must stay display-agnostic.** Do not set
  `QT_QPA_PLATFORM`, force offscreen plugins, or add headless-only flags inside
  the code base. Rely on the surrounding environment instead.

## Troubleshooting Qt on Linux containers

- Symptoms of missing libraries include: `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, "This application failed to start because no Qt
  platform plugin could be initialized", or loader errors such as
  `libEGL.so.1: cannot open shared object file`.

- Install the same dependencies used in CI, then retry with `QT_QPA_PLATFORM=xcb`
  and `xvfb-run`:

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
  ```

## License

PDF Toolbox is distributed under the terms of the [MIT License](LICENSE).

- After installing the libraries, rerun
  `xvfb-run -s "-screen 0 1920x1080x24" pre-commit run --all-files`.

## Read next

- [CONTRIBUTING](CONTRIBUTING.md) — contributor workflow and review checklist.
- [DEVELOPMENT](DEVELOPMENT.md) — maintainer notes, architecture, and testing
  guidance.
- [AGENTS](AGENTS.md) — enforcement rules for Codex agents and reviewers.
