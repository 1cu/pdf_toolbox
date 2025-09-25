# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                         | Reason                                                                | Issue/PR |
| ------------------------------------------------ | ---------------------------- | --------------------------------------------------------------------- | -------- |
| src/pdf_toolbox/gui/main_window.py:111           | PLR0915                      | constructor sets up many widgets                                      | -        |
| src/pdf_toolbox/gui/main_window.py:274           | PLR0912, PLR0915             | dynamic form builder is inherently complex                            | -        |
| src/pdf_toolbox/gui/main_window.py:526           | TRY004                       | GUI handler expects ValueError                                        | -        |
| src/pdf_toolbox/gui/main_window.py:773           | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:36                | type: ignore[override]       | QObject method signature differs from logging.Handler.emit            | -        |
| src/pdf_toolbox/gui/widgets.py:76                | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:81                | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:99                | N802                         | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/miro.py:715                      | PLR0913                      | export pipeline exposes optional tuning knobs                         | -        |
| src/pdf_toolbox/renderers/\_requests_types.py:28 | PLR0913                      | mirror requests.post signature for accuracy                           | -        |
| src/pdf_toolbox/renderers/ms_office.py:19        | pragma: no cover             | PowerPoint automation relies on pywin32                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:20        | type: ignore                 | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:22        | type: ignore                 | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:24        | pragma: no cover             | gracefully degrade without pywin32                                    | -        |
| src/pdf_toolbox/renderers/ms_office.py:25        | type: ignore[assignment]     | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:26        | type: ignore[assignment]     | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:27        | pragma: no cover             | PowerPoint COM only available on Windows                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:28        | type: ignore[assignment]     | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:29        | type: ignore[assignment]     | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:75        | pragma: no cover             | surface COM automation failure                                        | -        |
| src/pdf_toolbox/renderers/ms_office.py:104       | pragma: no cover             | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:134       | pragma: no cover             | propagate PowerPoint open failure                                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:161       | pragma: no cover             | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:175       | pragma: no cover             | guard unexpected COM errors                                           | -        |
| src/pdf_toolbox/renderers/ms_office.py:242       | pragma: no cover             | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/ms_office.py:311       | pragma: no cover             | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/registry.py:83         | BLE001, RUF100               | metadata backends can raise arbitrary errors; degrade to no plugins   | -        |
| src/pdf_toolbox/renderers/registry.py:106        | BLE001, RUF100               | plugin entry point import may fail arbitrarily; degrade to warning    | -        |
| src/pdf_toolbox/renderers/registry.py:125        | BLE001, RUF100               | plugin modules may be missing or broken; degrade to warning           | -        |
| src/pdf_toolbox/renderers/registry.py:174        | BLE001, RUF100               | builtin providers rely on optional platform modules; degrade to debug | -        |
| src/pdf_toolbox/renderers/registry.py:206        | BLE001, RUF100               | renderer constructors may fail arbitrarily; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:247        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:265        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable      | -        |
| tests/gui/conftest_qt.py:135                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:144                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:147                     | type: ignore[override]       | stub preserves Qt camelCase API                                       | -        |
| tests/gui/test_main_window.py:530                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:544                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:654                | N802                         | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:664                | type: ignore[assignment]     | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:746                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:750                | type: ignore[override]       | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:1179               | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/gui/test_widgets.py:124                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:131                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:142                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:145                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:187                    | N802                         | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:194                    | N802                         | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:204                    | N802                         | stub mirrors Qt event API                                             | -        |
| tests/gui/test_worker.py:40                      | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                            | -        |
| tests/test_gui_import.py:111                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:238                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_gui_import.py:243                     | type: ignore[attr-defined]   | stub Qt module for tests                                              | -        |
| tests/test_pptx_ms_office_renderer.py:22         | N802                         | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:26         | N802                         | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:47         | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:72         | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:78         | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:91         | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:108        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:121        | N802                         | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:126        | N802                         | COM style method name                                                 | -        |

<!-- mdformat on -->

## Runtime Exceptions

<!-- mdformat off -->

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                    |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx.no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-renderer) |

<!-- mdformat on -->
