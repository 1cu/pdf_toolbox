# Exception Refactor Assessment

This document reviews every entry in [`DEVELOPMENT_EXCEPTIONS.md`](../DEVELOPMENT_EXCEPTIONS.md) and outlines concrete refactoring or tooling options that would let us eventually remove the documented exception. The focus is on reducing the long-term maintenance burden by either fixing the underlying issue, isolating the behaviour behind better abstractions, or upstreaming the missing typing information.

Note: `DEVELOPMENT_EXCEPTIONS.md` is generated. Do not edit it manually—run `scripts/generate_exception_overview.py` instead.

## Progress

- [x] Vendored minimal PyMuPDF type stubs in `typings/fitz/__init__.pyi` so action
  modules and utilities no longer need blanket `type: ignore` comments when
  importing `fitz`. (2025-03-17)
- [x] Rebuilt the actions registry to persist metadata outside the decorated
  callables, ensuring reloads keep definitions discoverable without mutating the
  functions directly. (2025-03-17)

## Methodology

- Group the inline exceptions by file to understand their shared causes (using the latest regenerated overview).
- Inspect the affected implementation to confirm why the suppression is required today.
- Propose one or more refactorings, type stub additions, or testing strategies that remove the need for the suppression while keeping behaviour intact.
- Call out the work required (internal refactor, new helper, upstream contribution, etc.) and highlight blockers when the exception is currently unavoidable.

Prerequisite:

- Regenerate `DEVELOPMENT_EXCEPTIONS.md` with `scripts/generate_exception_overview.py` before revising this document.

## Detailed Review

### Typings package

- **`typings/fitz` naming**: Evaluate whether the vendored stubs should remain under
  the upstream module name or move behind a package-specific namespace (e.g.
  `pdf_toolbox._vendor.fitz`) with explicit re-exports to avoid confusing end
  users that the runtime library itself is bundled. Document whichever strategy
  we keep so contributors understand the distinction between runtime and typing
  shims.

### `src/pdf_toolbox/actions/__init__.py`

- **L87 – `type: ignore[attr-defined]`**: We attach `__pptx_renderer_required__` on the action function so the GUI can highlight renderer requirements. Refactor by storing this flag in the `Action` dataclass returned by `build_action` and pass it through the registry instead of mutating the callable. The decorator can look up the value in `_registry` when needed, eliminating the attribute injection.
- **L94 – `type: ignore[attr-defined]`**: Similar dynamic attribute attachment for `__pdf_toolbox_action__`. Replace with a dedicated registry (`_visible_actions`) or extend `Action` with a `visible` flag so discovery code no longer relies on attributes.

### `src/pdf_toolbox/actions/extract.py`

- **L8 – `type: ignore` (PyMuPDF)**: Introduce local `py.typed` stub files for the subset of PyMuPDF used by the project, or vendor the upstream `pymupdf-stubs` package if it covers the required surface. Once the module exports type information, the blanket ignore becomes unnecessary.

### `src/pdf_toolbox/actions/miro.py`

- **L27 – `PLR0913`**: The action exposes nine parameters to mirror the GUI form. Create a dataclass (e.g. `MiroExportOptions`) that groups related options (`server`, `quality`, file paths). The GUI can construct the dataclass instance and the action accepts a single argument, reducing the parameter count without losing clarity.

### `src/pdf_toolbox/actions/pdf_images.py`

- **L11 – `type: ignore` (PyMuPDF)**: Provide local stubs or a thin wrapper module with precise return types for the PyMuPDF objects we use.
- **L127 – `PLR0912`, `PLR0913`, `PLR0915`**: The rendering helper currently handles parameter validation, progress updates, and file management in one routine. Split it into composable helpers: (1) a configuration object describing requested outputs, (2) a validator that returns a normalised plan, and (3) a renderer that iterates the pages. Each helper stays under the complexity limit, and the public function can delegate accordingly.
- **L322 – `PLR0913`**: The conversion helper can accept a small configuration object (e.g. `ImageConversionRequest`) instead of five primitive arguments, reducing the parameter count.

### `src/pdf_toolbox/actions/pptx.py`

- **L19 – `PLR0913`**: Like the Miro action, create a `PptxExportOptions` dataclass that packages the action parameters and optional renderer specific overrides. The GUI can instantiate the dataclass before invoking the action.

### `src/pdf_toolbox/actions/unlock.py`

- **L8 – `type: ignore` (PyMuPDF)**: Covered by the PyMuPDF stub effort outlined for the other action modules.

### `src/pdf_toolbox/gui/__init__.py`

- **L44 – `pragma: no cover`**: This guard switches behaviour when Qt is unavailable. Add a small unit test that imports the module under `pytest.mark.qt_noop` and patches the Qt import to raise, asserting that the fallback path logs a helpful error. With the path exercised, the pragma can be removed.

### `src/pdf_toolbox/gui/main_window.py`

- **L87 – `PLR0915`**: The constructor wires up widgets, state, and configuration. Extract widget construction into dedicated factory methods (`_build_toolbar`, `_build_banner`, etc.) and rely on helper classes for complex sections (profile selection, action list). This shortens `__init__` below the branch threshold.
- **L165, L201 – `type: ignore[attr-defined]` (missing Qt enums)**: Ship local `.pyi` stub augmentations (`qt-stubs.pyi`) that expose the missing enum members (`QFormLayout.FieldGrowthPolicy`, `QToolButton.ToolButtonPopupMode`). Use `typing_extensions.override` where appropriate. Adding these definitions removes the ignores.
- **L232, L238 – `type: ignore[attr-defined]` (`Qt.UserRole`)**: Covered by the same stub augmentation—extend the QtCore stub to include `Qt.UserRole` and similar constants.
- **L244 – `PLR0912`, `PLR0915`**: `_build_form` mixes parameter inspection, widget selection, and config binding. Introduce a strategy registry mapping annotation types to widget factories, so each branch moves into its own function. The main loop can dispatch to these factories, reducing complexity.
- **L302 – `type: ignore[attr-defined]` (`types.UnionType`)**: Update the local PySide stubs to include `types.UnionType` in the `typing` utilities exported in Qt, or gate the branch using `if isinstance(ann, types.UnionType)` without referencing attributes flagged by the stub.
- **L402 – `type: ignore[arg-type]` and L403 – `type: ignore[assignment]`**: These lines unpack tuple values returned by the widget builder. Replace the tuple with a small dataclass representing the composite widget so type checkers understand the shape, or refactor `_collect_arguments` to handle the tuple via structural typing (`Protocol`).
- **L415 – `PLR0912`**: `_collect_arguments` handles data extraction and validation. Break it into two passes: (1) gather raw values, (2) validate and coerce. Each pass stays under the branch limit.
- **L430 – `type: ignore[attr-defined]` (Qt enum)**: Covered by stub augmentation.
- **L493 – `pragma: no cover`**: The method launches the documentation URL. Add an integration test that patches `QDesktopServices.openUrl` and asserts it receives the expected URL—this works under headless CI and removes the pragma.
- **L674 – `N802`**: The event handler must be named `changeEvent` to override the Qt virtual. Provide a thin adapter method (`def change_event(self, event): self.changeEvent(event)`) for code using snake_case while leaving the canonical override. Then mark the camelCase method as private or rely on `@override` to show it's intentional; if the snake_case wrapper becomes the public entry, the lint suppression can move to the wrapper or disappear entirely.
- **L709, L729, L753, L809 – `type: ignore[attr-defined]` (dialog button enum)** and **L713, L733, L757, L813 – `type: ignore[attr-defined]` (dialog attribute)**: Extend the Qt stub file with the missing `QMessageBox.StandardButton` and `QDialog.DialogCode` aliases. Alternatively, wrap the dialog creation in helper functions typed with `Literal` values so the return types remain precise without referencing the missing attributes directly.

### `src/pdf_toolbox/gui/widgets.py`

- **L36 – `type: ignore[override]`**: `QtLogHandler.emit` intentionally matches `logging.Handler.emit`, but PySide expects a QObject signature. Replace the QObject inheritance with composition—let the handler own a QObject that emits the signal—so the handler itself keeps the logging signature and the override ignore disappears.
- **L76, L81, L99 – `N802`**: These event handlers must remain camelCase for Qt. Follow the same adapter approach as `changeEvent`: provide snake_case wrappers or use `@override` annotations from `typing_extensions` to satisfy Ruff once it supports respecting overrides.

### `src/pdf_toolbox/image_utils.py`

- **L8 – `type: ignore` (PyMuPDF)**: Handled by the PyMuPDF stub effort.

### `src/pdf_toolbox/miro.py`

- **L13 – `type: ignore` (PyMuPDF)**: Covered by the stub plan.
- **L245, L260, L280, L300 – `pragma: no cover`**: These guard codec-specific fallbacks. Introduce parametrised tests that monkeypatch Pillow's feature flags to simulate missing encoders and assert the warning path. The tests can run quickly without relying on actual codec availability.
- **L693 – `pragma: no cover`**: This branch catches renderer crashes to keep the GUI responsive. Add a test that simulates a crash by raising from the worker thread and asserts the GUI shows the error banner, using Qt's test helpers.

### `src/pdf_toolbox/renderers/_http_util.py`

- **L8, L10, L26 – `pragma: no cover`**: Expand unit tests to import the module with and without `requests` available (`monkeypatch.sys.modules['requests'] = None`) and verify the fallback path. Use `pytest.mark.parametrize` to cover both scenarios.
- **L9, L30 – `type: ignore[...]` (requests typing)**: Add `types-requests` to `pyproject.toml` to provide full typing. Once installed, the import gains type information, eliminating the ignores. For the call site, annotate the `files` mapping with the precise `requests` type alias so the type checker accepts it.
- **L11 – `type: ignore[assignment]`**: Replace the sentinel `None` with a `typing.Protocol` that represents the subset of `requests` used. The fallback can then assign an instance of a local stub object conforming to the protocol without ignores.

### `src/pdf_toolbox/renderers/http_office.py`

- **L23, L25, L30 – `pragma: no cover`** and **L24, L26 – `type: ignore[...]`**: Apply the same `requests` protocol/stub strategy and extend tests to cover missing dependency scenarios, allowing removal of the pragmas and ignores.
- **L346 – `PLR0913`**: Introduce a configuration dataclass representing an HTTP rendering request (`HttpRenderJob`). Pass the dataclass to the renderer instead of eight discrete parameters.

### `src/pdf_toolbox/renderers/lightweight_stub.py`

- **L27 – `PLR0913`**: The lightweight renderer mirrors the full renderer API. Extract a shared `RenderOptions` dataclass used by all renderers so each implementation receives a single structured object.

### `src/pdf_toolbox/renderers/ms_office.py`

- **L19, L20, L22 – `type: ignore` (pywin32)**: Vendor or generate stubs for the specific COM interfaces used (`Dispatch`, `constants`, etc.), or depend on `pywin32-stubs`. With type information available, the ignores disappear.
- **L25, L26, L28, L29 – `type: ignore[assignment]`**: Replace module-level sentinels with explicit `typing.Protocol` objects that describe the COM interfaces. When pywin32 is unavailable, assign instances of lightweight sentinel classes implementing the protocol instead of `None`.
- **L27, L75, L104, L134, L161, L175, L242, L256, L312 – `pragma: no cover`**: These paths handle Windows-specific COM errors. Write platform-marked tests (`pytest.mark.windows`) that run under Windows CI to exercise the real COM integration. For non-Windows environments, factor the COM interactions into injectable collaborators and unit test them with fakes to cover error handling.
- **L256 – `PLR0913`**: Align with the shared `RenderOptions` dataclass described above.

### `src/pdf_toolbox/renderers/pptx.py`

- **L57 – `PLR0913`**: Adopt the shared `RenderOptions` object.

### `src/pdf_toolbox/renderers/pptx_base.py`

- **L22 – `PLR0913`**: Again solved by the common options dataclass.

### `src/pdf_toolbox/renderers/registry.py`

- **Multiple `BLE001`/`RUF100` entries**: The registry currently catches `Exception` to isolate plugin failures. Introduce a narrow custom exception (e.g. `RendererLoadError`) that wraps unexpected errors. Update plugin loading to catch known exception types (e.g. `ImportError`, `AttributeError`) explicitly and re-raise others after logging, reducing reliance on bare `Exception` catches. Alternatively, encapsulate the broad handling inside utility functions marked with `noqa` so the main flow avoids suppressions.

### `src/pdf_toolbox/utils.py`

- **L13 – `type: ignore` (PyMuPDF)**: Addressed by the PyMuPDF stub effort.

### `tests/conftest.py`

- **L4 – `type: ignore` (PyMuPDF)**: Covered by the stub addition.

### `tests/gui/conftest_qt.py`

- **CamelCase `N802` entries (L117, L120, L123, L126, L129, L132)**: Provide helper mixins that expose snake_case methods and internally delegate to Qt-style names, allowing the test stubs to comply with Ruff while still satisfying Qt. Alternatively, generate `.pyi` stub files for the Qt helpers so the runtime functions keep their camelCase names but Ruff ignores the stubs.
- **`type: ignore[override]` entries (L120, L129, L132)**: Switching to stub files also resolves the override mismatch because the implementation file no longer needs to inherit Qt types directly.
- **L172 – `type: ignore[attr-defined]`**: Extend the PySide stub with `QDialog.Accepted`.
- **L216 – `pragma: no cover`**: Add a test that instantiates the worker stub and triggers the method via Qt's event loop under Xvfb to prove the branch works.

### `tests/gui/test_main_window.py`

- **L502, L624 – `N802`**: Use snake_case wrapper helpers or mark the class with `@pytest.mark.qt_no_camel` to signal Ruff to skip, once available. Another option is to create a helper fixture returning a callable so the test functions no longer define camelCase names.
- **L516, L634 – `type: ignore[assignment]`**: Replace the simple namespace stubs with lightweight QObject subclasses defined in `.pyi` stub files, or use `cast(WorkerProtocol, stub)` to express intent without ignores.
- **L716, L720 – `type: ignore[override]`**: Define a `RendererProtocol` in tests and have the stub implement it explicitly, ensuring the override check passes.
- **L1082, L1109 – `type: ignore[...]`**: Model the worker injection via a `Protocol` that includes the dynamically added methods so the fixture can `cast` to the protocol rather than mutating a concrete class.

### `tests/gui/test_widgets.py`

- **CamelCase `N802` entries (L124, L131, L142, L145, L187, L194, L204)**: Similar adapter or stub strategies as the other Qt tests.
- **L222 – `type: ignore[attr-defined]`**: Expand the PySide stub to include `Qt.LeftButton`.

### `tests/gui/test_worker.py`

- **L40 – `type: ignore[no-untyped-def]`**: Define a `Protocol` for the worker callback that includes the dynamic event parameter. Typing the protocol removes the need for the ignore.

### `tests/renderers/test_http_office.py`

- **L219, L246, L480 – `type: ignore[import-untyped]`**: Resolved by adding `types-requests` and updating imports to reference the typed alias.

### `tests/test_actions.py`

- **L99 – `pragma: no cover`**: Convert the registry import test into an assertion that exercises the stub action body (e.g. call it with sample data) so the code path is covered.
- **L101, L103 – `type: ignore[attr-defined]`**: Instead of mutating the module during tests, expose an explicit test-only registration helper in `actions.__init__` that accepts a `visible` flag. Tests can call the helper without setting attributes.

### `tests/test_actions_e2e.py`, `tests/test_converters.py`, `tests/test_images.py`, `tests/test_utils.py`

- **`type: ignore` (PyMuPDF)**: Covered by the shared PyMuPDF stub strategy.

### `tests/test_miro.py`

- **L215 – `pragma: no cover`**: Exercise the dummy renderer branch by invoking it in tests and asserting the fallback behaviour, removing the pragma.

### `tests/test_pptx.py`, `tests/test_pptx_e2e.py`, `tests/test_pptx_renderer.py`, `tests/test_renderer_registry.py`, `tests/test_pptx_ms_office_renderer.py`

- **`PLR0913` occurrences**: Update the tests to construct the shared `RenderOptions` dataclass so helper functions no longer take many parameters.
- **`N802` entries in the COM renderer tests**: Generate `.pyi` stubs or adapter wrappers that expose snake_case helpers while keeping the COM-style naming confined to the stub layer. Tests can then call the snake_case helpers and satisfy Ruff.
- **`type: ignore[import-untyped]` in PPTX tests**: Also resolved via the `types-requests` dependency.

## Cross-Cutting Initiatives

1. **Provide third-party type information**: Creating or vendoring stub packages for PyMuPDF, PySide6 gaps, `requests`, and `pywin32` eliminates 63 ignores across the codebase.
1. **Adopt configuration dataclasses for actions/renderers**: A shared `RenderOptions` (and action-specific options) object removes 22 separate `PLR0913`/`PLR0912` suppressions in actions, renderers, and tests.
1. **Improve test coverage of exceptional paths**: Investing in faked codecs, dependency toggles, and Windows CI coverage allows us to drop 18 `pragma: no cover` markers.
1. **Introduce protocols/stub files for Qt integration**: Replacing runtime attribute hacks with well-typed protocols and `.pyi` files resolves 20 Qt-related ignores and naming suppressions.

Implementing these workstreams sequentially will steadily shrink `DEVELOPMENT_EXCEPTIONS.md` and make the remaining suppressions more visible for follow-up work.

## Maintenance Snapshot

- Based on `DEVELOPMENT_EXCEPTIONS.md` regenerated from commit `f49536ac05832c21ffa0cb0a306bfa3bf70e8453` on 2025-09-23 via `scripts/generate_exception_overview.py`.
