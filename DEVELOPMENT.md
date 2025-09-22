# Development

You maintain PDF Toolbox here. Use this guide alongside the concise overview in
[README](README.md), the contributor checklist in [CONTRIBUTING](CONTRIBUTING.md),
and the enforcement rules in [AGENTS](AGENTS.md).

## Read this first

- Python 3.13 is the only supported runtime. Ensure your local environment
  matches CI.
- Work inside the `src/pdf_toolbox` package; tests live under `tests` and helper
  scripts under `scripts`.
- Scripts are usually thin wrappers. `scripts/pin_actions.py` is the deliberate
  exception because it automates the workflow pinning process end to end.
- Discover architecture and API details through docstrings and your IDE. No
  Sphinx documentation exists.

## Set up the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
```

Use `pip install .[dev]` for a non-editable installation when the editable mode
isn't required.

On desktop Linux, macOS, and Windows machines run Qt against a real display and
exercise the fast suite with `pre-commit run tests --all-files`. In Linux-based
CI or container environments install the Qt X11/EGL libraries with the shared
script, export `QT_QPA_PLATFORM=xcb`, and rely on a virtual display:

```bash
# Typical CI or agent runner (non-root user)
sudo -E bash scripts/ci/install-qt-headless.sh

# Rooted containers
bash scripts/ci/install-qt-headless.sh

export QT_QPA_PLATFORM=xcb
xvfb-run -s "-screen 0 1920x1080x24" pre-commit run --all-files
```

Do not bake headless flags or `QT_QPA_PLATFORM` overrides into tests or
fixtures—leave display selection to the environment.

## Run the sources

Launch the Qt GUI entry point from source:

```bash
python -m pdf_toolbox.gui
```

The module `src/pdf_toolbox/gui/__main__.py` wires the window, background worker
threads, and action registry together.

## Understand the action framework

- Register new functionality with `@action` in `pdf_toolbox.actions`. The
  decorator records metadata, exposes the callable for scripting, and makes it
  discoverable by the GUI.
- The GUI inspects type hints and default values to build forms. Keep signatures
  explicit and prefer typed enums/`Literal` values for choice fields.
- Actions run in worker threads so long-running operations do not block the UI.
  Factor heavy lifting into reusable helpers under `pdf_toolbox` so they can be
  unit-tested without the GUI.

## Configure renderers and profiles

- User configuration lives in `pdf_toolbox_config.json` inside the directory
  returned by `platformdirs` (for example `~/.config/pdf_toolbox/`). Keys:
  - `author` and `email` populate document metadata and GUI prompts.
  - `pptx_renderer` chooses a renderer: omit or `null` for the default
    `NullRenderer`, `"ms_office"` for the COM-based renderer on Windows, and
    future plugin identifiers for additional providers.
- Renderer plugins implement `BasePptxRenderer` in
  `pdf_toolbox.renderers.pptx`. They register under the
  `pdf_toolbox.pptx_renderers` entry point group and expose
  `probe()`, `capabilities()`, `to_pdf()`, and `to_images()`.
- The GUI uses export profiles (including **Miro (optimised for Miro/Boards)**)
  to expose tuned defaults. Profiles live alongside their actions so they can be
  scripted without the GUI.

## Internationalise correctly

- Locale files reside in `src/pdf_toolbox/locales/en.json` and `de.json`. Keys
  include `actions`, `select_file`, `field_cannot_be_empty`, `input_pdf`,
  `out_dir`, and `max_size_mb`.
- Use the helper functions `tr(key, **kwargs)`, `label(name)`, and
  `set_language(language_code)` from `pdf_toolbox.i18n` instead of hard-coded
  strings.
- Update **both** locale files when adding keys. Keep JSON sorted and let
  `pre-commit` run the locale formatting hook.

## Log with the shared logger

Use the utilities in `pdf_toolbox.utils.logging` (imported via convenience
wrappers) for diagnostics. Avoid `print` and avoid inventing new logging setups;
Bandit runs in hooks and CI to catch insecure logging or file handling.

## Test effectively

- Run `pre-commit run tests --all-files` to execute `pytest` with coverage
  reporting. Hooks also run ruff, mypy, bandit, locale validation, and the
  coverage checker. CI mirrors the lint/format/security hooks via
  `pre-commit run --all-files --hook-stage manual`; keep the fast pytest hook
  green locally and trigger the manual `pytest-slow` stage when you change code
  covered by slow tests.
- Maintain ≥95% coverage overall **and per file**. The helper script
  `scripts/check_coverage.py` enforces per-file thresholds after pytest.
- Keep GUI-only components thin. Factor logic into pure helpers so you can cover
  it with tests. GUI widgets listed in `pyproject.toml` under coverage `omit`
  are the only accepted exclusions.
- Use fixtures such as `tmp_path` for filesystem interactions and prefer
  deterministic tests.

### GUI tests

- GUI smoke tests rely on [pytest-qt](https://pytest-qt.readthedocs.io/) and its
  `qtbot` fixture to manage the Qt event loop and simulate user interaction
  helpers such as `waitUntil`, `waitSignal`, and `mouseClick`.

- Run the focused GUI suite on a desktop session with:

  ```bash
  pytest -q -m gui
  ```

- In CI or Linux containers without a graphical session, rely on the
  environment to provide `QT_QPA_PLATFORM=xcb` and run via Xvfb:

  ```bash
  xvfb-run -s "-screen 0 1920x1080x24" pytest -q -m gui
  ```

- CI and automation run under `QT_QPA_PLATFORM=xcb` with an Xvfb server; tests
  must never set their own platform plugin or force offscreen rendering. Install
  the xcb support libraries using `scripts/ci/install-qt-headless.sh` so the Qt
  plugin can load on Ubuntu runners.

### Raising GUI coverage

The GUI modules are the last files exempted from the per-file coverage gate.
Expand the focused GUI suite before removing the `omit` entries in
`pyproject.toml`:

- Extend `tests/gui/conftest_qt.py` with reusable stubs for message boxes,
  dialogs, and worker threads so tests stay synchronous and deterministic.
- Cover the `MainWindow` life cycle: status updates, log toggles, PPTX banner
  refresh, profile persistence, and the success/error paths of `on_run`,
  `on_finished`, and `on_error`.
- Add targeted tests for the supporting widgets (`FileEdit`, `ClickableLabel`,
  `QtLogHandler`) to remove the remaining `# pragma: no cover` markers.
- Exercise `pdf_toolbox.gui.worker.Worker` with synchronous callables that hit
  the success, failure, and cancellation paths without spinning a real thread.
- Add a smoke test for `pdf_toolbox.gui.main` that patches `QApplication` and
  `MainWindow` to confirm the entry point is exercised once Qt is available.

Track progress with `pytest -q -m gui --cov=pdf_toolbox.gui` and reinstate the
default coverage gate once each branch is covered.

### Troubleshooting Qt on Linux containers

- Missing libraries often manifest as `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, "This application failed to start because no Qt
  platform plugin could be initialized", or loader errors mentioning
  `libEGL.so.1`.

- Install the CI dependency bundle with `scripts/ci/install-qt-headless.sh`
  (use `sudo -E` when not running as root) and rerun the suite under Xvfb:

  ```bash
  sudo -E bash scripts/ci/install-qt-headless.sh
  export QT_QPA_PLATFORM=xcb
  xvfb-run -s "-screen 0 1920x1080x24" pre-commit run --all-files
  ```

- On Linux containers, export `QT_QPA_PLATFORM=xcb` and run
  `xvfb-run -s "-screen 0 1920x1080x24" pre-commit run --all-files`.

### Slow tests & policy

- Tests that take **0.75 seconds or longer** (`tool.pytest.ini_options.slow_threshold`)
  must be optimised before being marked with `@pytest.mark.slow`. The
  `fail_on_unmarked_slow` toggle lives in `pyproject.toml` and defaults to
  enforcing the policy.

Example `pyproject.toml` configuration:

```toml
[tool.pytest.ini_options]
slow_threshold = "0.75"
fail_on_unmarked_slow = "true"
```

- The fast iteration loop (local commits, the pre-commit test hook, and the
  `tests-fast` CI job) runs the quick suite. Use the lightweight command below
  while iterating; coverage is still enforced by `pre-commit run tests --all-files`
  and the CI job, which append `--cov` flags and execute
  `python scripts/check_coverage.py`.

  ```bash
   pytest -n auto -m "not slow" --timeout=60 --maxfail=1 \
         --durations=0 --durations-min=0.75
  ```

- Execute the slow-only suite whenever you touch code that might regress
  performance:

  ```bash
  pytest -n auto -m "slow" -q --timeout=120 \
         --durations=0 --durations-min=0.75
  ```

- When you want the slow suite under pre-commit, run the manual stage hook:

  ```bash
  pre-commit run pytest-slow --hook-stage manual
  ```

- The fast suite fails automatically whenever an unmarked test exceeds the
  threshold. Optimise the test or mark it `@pytest.mark.slow` before merging.
  CI only starts the `tests-slow` phase once the fast phase succeeds.

## Manage exceptions deliberately

- When a linter, type-checker, bandit, or coverage rule truly cannot be fixed,
  add a one-line inline comment using the format:

  ```python
  import xml.etree.ElementTree as ET  # nosec B405  # pdf-toolbox: stdlib XML parser on trusted coverage file | issue:-
  ```

- Only single-line scopes are allowed; never use blanket `# noqa` or
  `# type: ignore` comments.

- Run `python scripts/generate_exception_overview.py` (or let pre-commit do it)
  to refresh `DEVELOPMENT_EXCEPTIONS.md`. Never edit that file manually.

- Review new exceptions during PR review and remove them once the underlying
  issue is resolved.

## Use the tooling

- `pre-commit run --all-files` executes the full suite of formatters, linters,
  tests, security checks, and the exception overview generator.

- Shortcuts exist:

  ```bash
  pre-commit run format --all-files
  pre-commit run lint --all-files
  pre-commit run tests --all-files
  ```

- CI runs the fast suite on Ubuntu (Python 3.13) before triggering the slow-only
  phase on the same platform. Both jobs install the dev extras and reuse the
  shared slow-policy hook so unmarked long-running tests fail quickly.

- We intentionally skip `pip-audit`; dependency publishing is out of scope for
  this project.

## Cut a release

1. Update `version` in `pyproject.toml`.
1. Commit the change and create a tag matching `v*` (for example `v0.6.21`).
1. Push the tag; the `release` workflow builds wheels and platform executables
   and attaches them to the GitHub release while pruning older artifacts.
1. Workflows pin third-party actions to immutable commit SHAs and periodically
   update to the latest stable release.
