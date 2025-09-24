# Exception Refactor Assessment

This document reviews every entry in [`DEVELOPMENT_EXCEPTIONS.md`](../DEVELOPMENT_EXCEPTIONS.md) and outlines concrete refactoring or tooling options that would let us eventually remove the documented exception. The focus is on reducing the long-term maintenance burden by either fixing the underlying issue, isolating the behaviour behind better abstractions, or upstreaming the missing typing information.

`DEVELOPMENT_EXCEPTIONS.md` is generated. Run `scripts/generate_exception_overview.py` before editing this plan so the catalogue reflects the current repository state.

## Progress

- [x] Split the optional `requests` import guard into `renderers/_requests.py`, enabling deterministic tests that simulate the dependency being missing.
- [x] Centralised Qt type augmentation in the GUI package, eliminating earlier ad-hoc stub files.

## Methodology

1. Regenerate `DEVELOPMENT_EXCEPTIONS.md` with `scripts/generate_exception_overview.py`.
2. Group the inline exceptions by file to understand their shared causes.
3. Inspect the affected implementation to confirm why the suppression is required today.
4. Propose the smallest refactor, stub addition, or test coverage improvement that removes the suppression without regressing behaviour.
5. Call out risks and prerequisites so the work can be scheduled realistically.

## Detailed Review

### `src/pdf_toolbox/cli.py`

- **Pragmas at L92, L102, L460, L475**: These branches surface argparse/help output and user-facing error messages. Add integration tests that invoke the CLI via `subprocess.run` (or `CliRunner`) and assert on the exit code and stderr output for the help and error paths. Once covered, the pragmas can be removed.

### `src/pdf_toolbox/gui/__init__.py`

- **Pragmas at L23, L27, L70**: Move the optional Qt import guard into a small helper (`_load_qt() -> tuple[type[QObject], ...]`) that can be unit-tested by patching `importlib.import_module`. With an explicit helper, we can exercise both the success and fallback branches without relying on pragmas.

### `src/pdf_toolbox/gui/main_window.py`

- **L109 – `PLR0915`**: Extract widget assembly into focused helpers (`_build_toolbar`, `_build_profile_controls`, etc.) and let the constructor orchestrate the calls. This reduces the branch count and improves readability.
- **L272 – `PLR0912`, `PLR0915`**: `_build_form` performs annotation inspection, widget construction, and binding. Introduce a registry mapping parameter annotations to `WidgetFactory` objects; each factory returns a dataclass describing the widget plus binding metadata. Dispatching through the registry keeps the main loop simple.
- **L524 – `TRY004`**: Replace the broad `try/except ValueError` with a helper that validates user input and returns a `Result` object (`Ok`/`Err`). The handler can switch on the result instead of relying on exceptions for flow control.
- **L593 – `pragma: no cover`**: Add a test that monkeypatches `QDesktopServices.openUrl` and triggers the action via the window. Use Qt's test harness to avoid opening a real browser.
- **L773 – `N802`**: Provide a thin snake_case wrapper (e.g. `def change_event(self, event): self.changeEvent(event)`) and update call sites to use the wrapper, letting the Qt override keep its camelCase name while satisfying Ruff.

### `src/pdf_toolbox/gui/widgets.py`

- **L36 – `type: ignore[override]`**: Replace inheritance from `QObject` with composition. Create a `QtLogEmitter(QObject)` helper that exposes the signal, and let the handler delegate to it. The handler keeps the `logging.Handler` signature, removing the override conflict.
- **L76, L81, L99 – `N802`**: Similar to the main window, add snake_case delegators or mark the overrides with `typing_extensions.override` once available to Ruff so the camelCase method names are recognised as intentional.

### `src/pdf_toolbox/miro.py`

- **Pragmas at L247, L262, L282, L302**: Parameterise tests to toggle Pillow codec availability (`monkeypatch(PIL.features, "check", ...)`) and assert that each fallback branch logs the expected warning. With coverage in place, the pragmas can be removed.
- **L695 – `pragma: no cover`**: Simulate renderer failures by creating a fake worker that raises and assert that the GUI path shows the error banner. Use Qt's test fixtures to avoid threading flakiness.
- **L715 – `PLR0913`**: Introduce a `MiroExportOptions` dataclass grouping the optional tuning knobs (`quality`, `scale`, etc.) so the action accepts a single object. Update the GUI form builder to produce the dataclass.

### `src/pdf_toolbox/renderers/_http_util.py`

- **L23 – `pragma: no cover`**: Extract the dependency check into a helper that accepts an injectable `requests` module. Tests can pass `None` to cover the fallback branch.

### `src/pdf_toolbox/renderers/_requests.py`

- **Pragmas at L12, L17, L19**: Add targeted tests that monkeypatch `sys.modules` to raise `ImportError` for `requests` and confirm the helper returns the sentinel object. With deterministic tests, the pragmas are no longer necessary.

### `src/pdf_toolbox/renderers/_requests_types.py`

- **L28 – `PLR0913`**: Replace the free function mirroring `requests.post` with a `Protocol` (`RequestsPoster`) and pass instances around. The helper can accept keyword-only arguments bundled in a dataclass to drop the parameter count.

### `src/pdf_toolbox/renderers/ms_office.py`

- **Pragmas at L19, L24, L27, L75, L104, L134, L161, L175, L242, L311**: Split Windows-specific behaviour into a collaborator class (e.g. `PowerPointAutomation`). Provide a fake implementation in tests so each error-handling branch is exercised. For non-Windows platforms, mark the tests with `pytest.mark.windows` and rely on CI coverage.
- **`type: ignore` entries at L20, L22**: Vendor minimal `.pyi` stubs for the subset of pywin32 used (`Dispatch`, `constants`, etc.) or depend on `pywin32-stubs`. Update `pyproject.toml` accordingly and re-run the type checker.
- **`type: ignore[assignment]` entries at L25, L26, L28, L29**: Replace sentinel `None` assignments with protocol-driven fake objects that implement the required methods, allowing type checkers to validate the assignments.
- **L20 – `type: ignore` (module import)**: Wrap the import in a helper returning a protocol-compliant wrapper. Tests can supply a fake to verify behaviour without ignores.

### `src/pdf_toolbox/renderers/registry.py`

- **`BLE001`/`RUF100` at L83, L106, L125, L174, L206, L247, L265**: Introduce a custom exception (`RendererRegistryError`) and restrict the broad `except Exception` blocks to the specific errors we expect (`ImportError`, `AttributeError`). For truly unknown exceptions, let them bubble up so Ruff no longer flags the bare catches. Alternatively, encapsulate the broad catch inside a helper decorated with `noqa` and document the rationale in code.

### `tests/gui/conftest_qt.py`

- **L117, L120, L123, L126, L129, L132 – `N802`**: Move the camelCase helpers into a `.pyi` stub file so Ruff analyses the stub instead of the implementation. Alternatively, provide snake_case wrappers that delegate to the camelCase functions used by Qt.
- **L120, L129, L132 – `type: ignore[override]`**: Switching to stub files (above) also resolves the override mismatch because the runtime functions no longer inherit from Qt types.
- **L218 – `N802`, `pragma: no cover`**: Add a unit test that instantiates the worker stub and triggers the camelCase method through Qt's event loop. Once covered, the pragma can be removed.

### `tests/gui/test_main_window.py`

- **L529, L653 – `N802`**: Replace camelCase helper functions with fixtures returning callables, or apply snake_case wrappers that call through to the camelCase Qt API.
- **L543, L663 – `type: ignore[assignment]`**: Define a `WorkerProtocol` representing the injected stub and cast accordingly, or implement a lightweight QObject subclass that satisfies the assignment.
- **L745, L749 – `type: ignore[override]`**: Introduce a `RendererProtocol` in the tests and have the stubs implement it so the override check passes.
- **L1113 – `type: ignore[no-untyped-def]`**: Annotate the injected event parameter via a `Protocol` and use `typing_extensions.TypeAlias` to express the callable type.

### `tests/gui/test_widgets.py`

- **`N802` entries at L124, L131, L142, L145, L187, L194, L204**: Same approach as other Qt tests—delegate through snake_case wrappers or move the camelCase definitions into stub files consumed only by Qt.

### `tests/gui/test_worker.py`

- **L40 – `type: ignore[no-untyped-def]`**: Define a `WorkerCallback` protocol that explicitly includes the dynamically injected `Event` parameter so the function signature is fully typed.

### `tests/test_gui_import.py`

- **L82, L87 – `type: ignore[attr-defined]`**: Provide a stub module (`tests/stubs/qt_module.pyi`) exporting the required attributes. Import the stub in tests so the runtime assignment no longer requires `type: ignore`.

### `tests/test_miro.py`

- **L250 – `pragma: no cover`**: Expand the dummy renderer test to assert on the fallback behaviour so the branch executes under coverage.

### `tests/test_pptx_ms_office_renderer.py`

- **N802 entries at multiple lines**: Create helper fixtures with snake_case names that internally call the COM-style camelCase methods. Update tests to use the helpers so Ruff no longer complains about the method names.

## Cross-Cutting Initiatives

1. **Third-party stubs**: Vendor or depend on stubs for PySide6 gaps and pywin32 so the GUI and Windows renderers compile cleanly without `type: ignore` noise.
2. **Qt wrapper strategy**: Standardise on snake_case wrappers around camelCase Qt hooks, and ensure Ruff respects the intent via `typing_extensions.override` or dedicated stub files.
3. **Dependency guards**: Encapsulate optional dependency checks in helper functions and add deterministic tests that toggle availability, eliminating `pragma: no cover` markers around import guards.
4. **Dataclass/Protocol adoption**: Replace long parameter lists and loose sentinel objects with dataclasses and protocols so type checkers understand the API and Ruff's complexity rules are easier to satisfy.

## Maintenance Snapshot

- Based on `DEVELOPMENT_EXCEPTIONS.md` regenerated from commit `f49536ac05832c21ffa0cb0a306bfa3bf70e8453`.
