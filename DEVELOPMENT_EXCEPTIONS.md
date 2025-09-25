# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                         | Reason                                                                | Issue/PR |
| ------------------------------------------------ | ---------------------------- | --------------------------------------------------------------------- | -------- |
| src/pdf_toolbox/gui/main_window.py:111           | PLR0915                      | constructor sets up many widgets                                      | -        |
| src/pdf_toolbox/gui/main_window.py:281           | PLR0912, PLR0915             | dynamic form builder is inherently complex                            | -        |
| src/pdf_toolbox/gui/main_window.py:533           | TRY004                       | GUI handler expects ValueError                                        | -        |
| src/pdf_toolbox/gui/main_window.py:837           | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:38                | type: ignore[override]       | QObject method signature differs from logging.Handler.emit            | -        |
| src/pdf_toolbox/gui/widgets.py:132               | N802                         | QSyntaxHighlighter requires camelCase hook name                       | -        |
| src/pdf_toolbox/gui/widgets.py:295               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:300               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:318               | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/miro.py:715                      | PLR0913                      | export pipeline exposes optional tuning knobs                         | -        |
| src/pdf_toolbox/renderers/\_requests_types.py:28 | PLR0913                      | mirror requests.post signature for accuracy                           | -        |
| src/pdf_toolbox/renderers/registry.py:85         | BLE001, RUF100               | metadata backends can raise arbitrary errors; degrade to no plugins   | -        |
| src/pdf_toolbox/renderers/registry.py:108        | BLE001, RUF100               | plugin entry point import may fail arbitrarily; degrade to warning    | -        |
| src/pdf_toolbox/renderers/registry.py:127        | BLE001, RUF100               | plugin modules may be missing or broken; degrade to warning           | -        |
| src/pdf_toolbox/renderers/registry.py:176        | BLE001, RUF100               | builtin providers rely on optional platform modules; degrade to debug | -        |
| src/pdf_toolbox/renderers/registry.py:208        | BLE001, RUF100               | renderer constructors may fail arbitrarily; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:249        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:267        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| tests/gui/conftest_qt.py:135                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:144                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:147                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/test_main_window.py:530                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:544                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:654                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:664                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:746                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:750                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:1238               | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/gui/test_widgets.py:129                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:136                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:147                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:150                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:192                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:199                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:209                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_worker.py:40                      | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/test_gui_import.py:111                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:240                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:245                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
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
