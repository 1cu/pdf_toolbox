# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                         | Reason                                                                | Issue/PR |
| ------------------------------------------------ | ---------------------------- | --------------------------------------------------------------------- | -------- |
| src/pdf_toolbox/actions/ocr.py:162               | type: ignore[attr-defined]   | pymupdf stubs lack extract_image                                      | -        |
| src/pdf_toolbox/gui/main_window.py:111           | PLR0915                      | constructor sets up many widgets                                      | -        |
| src/pdf_toolbox/gui/main_window.py:562           | TRY004                       | GUI handler expects ValueError                                        | -        |
| src/pdf_toolbox/gui/main_window.py:808           | PLR0911                      | widget type dispatch requires multiple returns                        | -        |
| src/pdf_toolbox/gui/main_window.py:848           | BLE001, RUF100               | GUI settings save errors should not block execution                   | -        |
| src/pdf_toolbox/gui/main_window.py:867           | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:145               | N802                         | QSyntaxHighlighter requires camelCase hook name                       | -        |
| src/pdf_toolbox/gui/widgets.py:306               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:311               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:329               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/miro.py:363                      | PLR0913                      | DPI search needs explicit bounds and bookkeeping                      | -        |
| src/pdf_toolbox/miro.py:476                      | PLR0913                      | selection requires explicit parameters to trace tuning                | -        |
| src/pdf_toolbox/miro.py:671                      | PLR0913, PLR0915             | export flow needs explicit inputs and branching for warnings          | -        |
| src/pdf_toolbox/miro.py:785                      | PLR0913                      | export pipeline exposes optional tuning knobs                         | -        |
| src/pdf_toolbox/paths.py:52                      | TRY003                       | path validation error message                                         | -        |
| src/pdf_toolbox/renderers/\_requests_types.py:28 | PLR0913                      | mirror requests.post signature for accuracy                           | -        |
| src/pdf_toolbox/renderers/http_office.py:236     | B104, S104                   | checking for blocked addresses, not binding                           | -        |
| src/pdf_toolbox/renderers/http_office.py:237     | TRY003                       | error messages specific to SSRF validation context                    | -        |
| src/pdf_toolbox/renderers/http_office.py:244     | TRY003                       | error messages specific to SSRF validation context                    | -        |
| src/pdf_toolbox/renderers/http_office.py:251     | TRY003                       | error messages specific to SSRF validation context                    | -        |
| src/pdf_toolbox/renderers/http_office.py:258     | PLR2004                      | RFC1918 private range 172.16-172.31                                   | -        |
| src/pdf_toolbox/renderers/http_office.py:259     | TRY003                       | error messages specific to SSRF validation context                    | -        |
| src/pdf_toolbox/renderers/registry.py:145        | BLE001, RUF100               | builtin providers rely on optional platform modules; degrade to debug | -        |
| src/pdf_toolbox/renderers/registry.py:252        | BLE001, RUF100               | metadata backends can raise arbitrary errors; degrade to no plugins   | -        |
| src/pdf_toolbox/renderers/registry.py:275        | BLE001, RUF100               | plugin entry point import may fail arbitrarily; degrade to warning    | -        |
| src/pdf_toolbox/renderers/registry.py:294        | BLE001, RUF100               | plugin modules may be missing or broken; degrade to warning           | -        |
| src/pdf_toolbox/renderers/registry.py:326        | BLE001, RUF100               | renderer constructors may fail arbitrarily; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:367        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:385        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| tests/gui/conftest_qt.py:208                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:217                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:220                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/test_e2e_pdf_images.py:11              | pragma: no cover             | skip when PySide6 missing                                             | -        |
| tests/gui/test_main_window.py:515                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:529                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:639                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:649                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:727                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:731                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:1216               | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/gui/test_settings_persistence.py:89        | S108                         | test fixture path only                                                | -        |
| tests/gui/test_settings_persistence.py:90        | S108                         | test fixture path only                                                | -        |
| tests/gui/test_widgets.py:127                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:134                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:145                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:148                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:190                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:197                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:207                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_worker.py:38                      | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/test_actions_security.py:183               | TRY003                       | test helper error message                                             | -        |
| tests/test_gui_import.py:111                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:239                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:244                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_pptx_ms_office_renderer.py:53         | N802                         | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:57         | N802                         | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:78         | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:103        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:109        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:122        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:139        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:152        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:157        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:295        | N802                         | COM style name                                                        | -        |
| tests/test_pptx_ms_office_renderer.py:488        | N802                         | COM style name                                                        | -        |

<!-- mdformat on -->

## Runtime Exceptions

<!-- mdformat off -->

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                    |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx.no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-renderer) |

<!-- mdformat on -->
