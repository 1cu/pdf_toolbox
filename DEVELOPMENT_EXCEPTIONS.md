# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                         | Reason                                                                    | Issue/PR |
| ------------------------------------------------ | ---------------------------- | ------------------------------------------------------------------------- | -------- |
| src/pdf_toolbox/actions/pdf_images.py:127        | PLR0912, PLR0913, PLR0915    | rendering pages needs many parameters and branches                        | -        |
| src/pdf_toolbox/actions/pdf_images.py:322        | PLR0913                      | conversion helper requires many parameters                                | -        |
| src/pdf_toolbox/cli.py:92                        | pragma: no cover             | delegate help/usage exit codes to argparse                                | -        |
| src/pdf_toolbox/cli.py:102                       | pragma: no cover             | runtime errors bubble up to stderr for CLI users                          | -        |
| src/pdf_toolbox/cli.py:460                       | pragma: no cover             | preserve conversion error text for numeric parameters                     | -        |
| src/pdf_toolbox/cli.py:475                       | pragma: no cover             | surface constructor failures from custom annotations                      | -        |
| src/pdf_toolbox/gui/\_\_init\_\_.py:44           | pragma: no cover             | environment dependent                                                     | -        |
| src/pdf_toolbox/gui/main_window.py:109           | PLR0915                      | constructor sets up many widgets                                          | -        |
| src/pdf_toolbox/gui/main_window.py:272           | PLR0912, PLR0915             | dynamic form builder is inherently complex                                | -        |
| src/pdf_toolbox/gui/main_window.py:524           | TRY004                       | GUI handler expects ValueError                                            | -        |
| src/pdf_toolbox/gui/main_window.py:593           | pragma: no cover             | opens external documentation                                              | -        |
| src/pdf_toolbox/gui/main_window.py:773           | N802                         | Qt requires camelCase event name                                          | -        |
| src/pdf_toolbox/gui/widgets.py:36                | type: ignore[override]       | QObject method signature differs from logging.Handler.emit                | -        |
| src/pdf_toolbox/gui/widgets.py:76                | N802                         | Qt requires camelCase event name                                          | -        |
| src/pdf_toolbox/gui/widgets.py:81                | N802                         | Qt requires camelCase event name                                          | -        |
| src/pdf_toolbox/gui/widgets.py:99                | N802                         | Qt requires camelCase event name                                          | -        |
| src/pdf_toolbox/miro.py:247                      | pragma: no cover             | guard against environment-specific WebP encoder issues                    | -        |
| src/pdf_toolbox/miro.py:262                      | pragma: no cover             | Pillow sometimes lacks WebP support                                       | -        |
| src/pdf_toolbox/miro.py:282                      | pragma: no cover             | PNG encoder failure varies by platform                                    | -        |
| src/pdf_toolbox/miro.py:302                      | pragma: no cover             | JPEG encoder may be unavailable                                           | -        |
| src/pdf_toolbox/miro.py:695                      | pragma: no cover             | keep GUI responsive despite renderer crashes                              | -        |
| src/pdf_toolbox/miro.py:715                      | PLR0913                      | export pipeline exposes optional tuning knobs                             | -        |
| src/pdf_toolbox/renderers/\_http_util.py:23      | pragma: no cover             | renderer checks dependency availability before calling helper             | -        |
| src/pdf_toolbox/renderers/\_requests.py:12       | pragma: no cover             | optional dependency import guard exercised via unit tests                 | -        |
| src/pdf_toolbox/renderers/\_requests.py:17       | pragma: no cover             | optional dependency missing                                               | -        |
| src/pdf_toolbox/renderers/\_requests.py:19       | pragma: no cover             | environments may raise arbitrary errors during import; degrade gracefully | -        |
| src/pdf_toolbox/renderers/\_requests_types.py:28 | PLR0913                      | mirror requests.post signature for accuracy                               | -        |
| src/pdf_toolbox/renderers/http_office.py:338     | PLR0913                      | renderer API requires many parameters                                     | -        |
| src/pdf_toolbox/renderers/lightweight_stub.py:27 | PLR0913                      | renderer API requires many parameters                                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:19        | pragma: no cover             | PowerPoint automation relies on pywin32                                   | -        |
| src/pdf_toolbox/renderers/ms_office.py:20        | type: ignore                 | pywin32 is optional and lacks type hints                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:22        | type: ignore                 | pywin32 is optional and lacks type hints                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:24        | pragma: no cover             | gracefully degrade without pywin32                                        | -        |
| src/pdf_toolbox/renderers/ms_office.py:25        | type: ignore[assignment]     | treat missing pywin32 as absent backend                                   | -        |
| src/pdf_toolbox/renderers/ms_office.py:26        | type: ignore[assignment]     | treat missing pywin32 as absent backend                                   | -        |
| src/pdf_toolbox/renderers/ms_office.py:27        | pragma: no cover             | PowerPoint COM only available on Windows                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:28        | type: ignore[assignment]     | COM unsupported on non-Windows platforms                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:29        | type: ignore[assignment]     | COM unsupported on non-Windows platforms                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:75        | pragma: no cover             | surface COM automation failure                                            | -        |
| src/pdf_toolbox/renderers/ms_office.py:104       | pragma: no cover             | propagate COM initialisation failure                                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:134       | pragma: no cover             | propagate PowerPoint open failure                                         | -        |
| src/pdf_toolbox/renderers/ms_office.py:161       | pragma: no cover             | propagate COM initialisation failure                                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:175       | pragma: no cover             | guard unexpected COM errors                                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:242       | pragma: no cover             | propagate COM export failure                                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:256       | PLR0913                      | renderer API requires many parameters                                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:312       | pragma: no cover             | propagate COM export failure                                              | -        |
| src/pdf_toolbox/renderers/pptx.py:57             | PLR0913                      | renderer API requires many parameters                                     | -        |
| src/pdf_toolbox/renderers/pptx_base.py:22        | PLR0913                      | renderer API requires many parameters                                     | -        |
| src/pdf_toolbox/renderers/registry.py:83         | BLE001, RUF100               | metadata backends can raise arbitrary errors; degrade to no plugins       | -        |
| src/pdf_toolbox/renderers/registry.py:106        | BLE001, RUF100               | plugin entry point import may fail arbitrarily; degrade to warning        | -        |
| src/pdf_toolbox/renderers/registry.py:125        | BLE001, RUF100               | plugin modules may be missing or broken; degrade to warning               | -        |
| src/pdf_toolbox/renderers/registry.py:174        | BLE001, RUF100               | builtin providers rely on optional platform modules; degrade to debug     | -        |
| src/pdf_toolbox/renderers/registry.py:206        | BLE001, RUF100               | renderer constructors may fail arbitrarily; treat as unavailable          | -        |
| src/pdf_toolbox/renderers/registry.py:247        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable          | -        |
| src/pdf_toolbox/renderers/registry.py:265        | BLE001, RUF100               | plugin can_handle implementations may fail; treat as unavailable          | -        |
| tests/gui/conftest_qt.py:117                     | N802                         | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:120                     | N802, type: ignore[override] | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:123                     | N802                         | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:126                     | N802                         | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:129                     | N802, type: ignore[override] | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:132                     | N802, type: ignore[override] | stub preserves Qt camelCase API                                           | -        |
| tests/gui/conftest_qt.py:218                     | N802, pragma: no cover       | method name follows Qt worker API                                         | -        |
| tests/gui/test_main_window.py:529                | N802                         | mimic Qt worker API naming                                                | -        |
| tests/gui/test_main_window.py:543                | type: ignore[assignment]     | stub worker lacks QObject base class                                      | -        |
| tests/gui/test_main_window.py:653                | N802                         | mimic Qt worker API naming                                                | -        |
| tests/gui/test_main_window.py:663                | type: ignore[assignment]     | stub worker lacks QObject base class                                      | -        |
| tests/gui/test_main_window.py:745                | type: ignore[override]       | stub implements abstract renderer for tests                               | -        |
| tests/gui/test_main_window.py:749                | type: ignore[override]       | stub implements abstract renderer for tests                               | -        |
| tests/gui/test_main_window.py:1113               | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                                | -        |
| tests/gui/test_widgets.py:124                    | N802                         | stub mirrors Qt URL API                                                   | -        |
| tests/gui/test_widgets.py:131                    | N802                         | stub mirrors Qt MIME API                                                  | -        |
| tests/gui/test_widgets.py:142                    | N802                         | stub mirrors Qt event API                                                 | -        |
| tests/gui/test_widgets.py:145                    | N802                         | stub mirrors Qt event API                                                 | -        |
| tests/gui/test_widgets.py:187                    | N802                         | stub mirrors Qt URL API                                                   | -        |
| tests/gui/test_widgets.py:194                    | N802                         | stub mirrors Qt MIME API                                                  | -        |
| tests/gui/test_widgets.py:204                    | N802                         | stub mirrors Qt event API                                                 | -        |
| tests/gui/test_worker.py:40                      | type: ignore[no-untyped-def] | Worker injects Event parameter dynamically                                | -        |
| tests/test_miro.py:250                           | pragma: no cover             | ensure dummy renderer keeps simple coverage                               | -        |
| tests/test_pptx.py:86                            | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx.py:177                           | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx.py:267                           | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx.py:340                           | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx.py:411                           | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx_e2e.py:78                        | PLR0913                      | renderer API requires many parameters                                     | -        |
| tests/test_pptx_ms_office_renderer.py:21         | N802                         | mirror COM method name                                                    | -        |
| tests/test_pptx_ms_office_renderer.py:25         | N802                         | mirror COM method name                                                    | -        |
| tests/test_pptx_ms_office_renderer.py:46         | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:71         | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:77         | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:90         | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:107        | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:120        | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_ms_office_renderer.py:125        | N802                         | COM style method name                                                     | -        |
| tests/test_pptx_renderer.py:20                   | PLR0913                      | renderer stub matches renderer API signature                              | -        |
| tests/test_renderer_registry.py:12               | PLR0913                      | renderer API requires many parameters                                     | -        |

<!-- mdformat on -->

## Runtime Exceptions

<!-- mdformat off -->

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                    |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx.no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-renderer) |

<!-- mdformat on -->
