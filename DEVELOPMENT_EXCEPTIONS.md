# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                          | Reason                                                                | Issue/PR |
| ------------------------------------------------ | ----------------------------- | --------------------------------------------------------------------- | -------- |
| scripts/check_coverage.py:8                      | B405                          | stdlib XML parser on trusted coverage file                            | -        |
| scripts/check_coverage.py:38                     | B314                          | parsing trusted coverage report                                       | -        |
| scripts/generate_exception_overview.py:53        | PLR0912                       | parsing requires several branches                                     | -        |
| scripts/pin_actions.py:150                       | S310                          | validated HTTPS request to GitHub API                                 | -        |
| scripts/pin_actions.py:154                       | S310, B310                    | GitHub API requests rely on urllib with pinned CA bundle              | -        |
| scripts/pin_actions.py:159                       | pragma: no cover              | log and rethrow network errors for diagnostics                        | -        |
| scripts/prune_releases.py:28                     | S310                          | urllib Request for GitHub API                                         | -        |
| scripts/prune_releases.py:33                     | S310, B310                    | urllib urlopen for GitHub API                                         | -        |
| scripts/prune_releases.py:60                     | type: ignore[arg-type]        | GitHub API returns untyped data                                       | -        |
| src/pdf_toolbox/actions/\_\_init\_\_.py:87       | type: ignore[attr-defined]    | attach renderer flag for GUI                                          | -        |
| src/pdf_toolbox/actions/\_\_init\_\_.py:94       | type: ignore[attr-defined]    | attach custom attribute for action registration                       | -        |
| src/pdf_toolbox/actions/extract.py:8             | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/actions/miro.py:27               | PLR0913                       | action signature mirrors GUI form                                     | -        |
| src/pdf_toolbox/actions/pdf_images.py:11         | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/actions/pdf_images.py:127        | PLR0913, PLR0912, PLR0915     | rendering pages needs many parameters and branches                    | -        |
| src/pdf_toolbox/actions/pdf_images.py:322        | PLR0913                       | conversion helper requires many parameters                            | -        |
| src/pdf_toolbox/actions/pptx.py:19               | PLR0913                       | action interface requires many parameters                             | -        |
| src/pdf_toolbox/actions/unlock.py:8              | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/gui/\_\_init\_\_.py:44           | pragma: no cover              | environment dependent                                                 | -        |
| src/pdf_toolbox/gui/main_window.py:87            | PLR0915                       | constructor sets up many widgets                                      | -        |
| src/pdf_toolbox/gui/main_window.py:165           | type: ignore[attr-defined]    | PySide6 stubs miss form layout policy enum                            | -        |
| src/pdf_toolbox/gui/main_window.py:201           | type: ignore[attr-defined]    | PySide6 stubs miss tool button enum                                   | -        |
| src/pdf_toolbox/gui/main_window.py:232           | type: ignore[attr-defined]    | PySide6 stubs miss Qt.UserRole                                        | -        |
| src/pdf_toolbox/gui/main_window.py:238           | type: ignore[attr-defined]    | PySide6 stubs miss Qt.UserRole                                        | -        |
| src/pdf_toolbox/gui/main_window.py:244           | PLR0912, PLR0915              | dynamic form builder is inherently complex                            | -        |
| src/pdf_toolbox/gui/main_window.py:302           | type: ignore[attr-defined]    | `types.UnionType` absent from stubs                                   | -        |
| src/pdf_toolbox/gui/main_window.py:402           | type: ignore[arg-type]        | PySide6 stubs reject tuple variant                                    | -        |
| src/pdf_toolbox/gui/main_window.py:403           | type: ignore[assignment]      | tuple already handled                                                 | -        |
| src/pdf_toolbox/gui/main_window.py:412           | PLR0912                       | argument collection involves many branches                            | -        |
| src/pdf_toolbox/gui/main_window.py:427           | type: ignore[attr-defined]    | PySide6 stubs miss Qt enum                                            | -        |
| src/pdf_toolbox/gui/main_window.py:490           | pragma: no cover              | opens external documentation                                          | -        |
| src/pdf_toolbox/gui/main_window.py:671           | N802                          | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/main_window.py:706           | type: ignore[attr-defined]    | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:710           | type: ignore[attr-defined]    | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:726           | type: ignore[attr-defined]    | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:730           | type: ignore[attr-defined]    | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:750           | type: ignore[attr-defined]    | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:754           | type: ignore[attr-defined]    | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:806           | type: ignore[attr-defined]    | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:810           | type: ignore[attr-defined]    | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/widgets.py:36                | type: ignore[override]        | QObject method signature differs from logging.Handler.emit            | -        |
| src/pdf_toolbox/gui/widgets.py:76                | N802                          | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:81                | N802                          | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:99                | N802                          | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/image_utils.py:8                 | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/miro.py:13                       | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/miro.py:245                      | pragma: no cover              | guard against environment-specific WebP encoder issues                | -        |
| src/pdf_toolbox/miro.py:260                      | pragma: no cover              | Pillow sometimes lacks WebP support                                   | -        |
| src/pdf_toolbox/miro.py:280                      | pragma: no cover              | PNG encoder failure varies by platform                                | -        |
| src/pdf_toolbox/miro.py:300                      | pragma: no cover              | JPEG encoder may be unavailable                                       | -        |
| src/pdf_toolbox/miro.py:693                      | pragma: no cover              | keep GUI responsive despite renderer crashes                          | -        |
| src/pdf_toolbox/renderers/\_http_util.py:8       | pragma: no cover              | optional dependency import guard exercised via unit tests             | -        |
| src/pdf_toolbox/renderers/\_http_util.py:9       | type: ignore[import-untyped]  | requests library does not ship type information                       | -        |
| src/pdf_toolbox/renderers/\_http_util.py:10      | pragma: no cover              | gracefully handle missing optional dependency                         | -        |
| src/pdf_toolbox/renderers/\_http_util.py:11      | type: ignore[assignment]      | sentinel assignment when dependency unavailable                       | -        |
| src/pdf_toolbox/renderers/\_http_util.py:26      | pragma: no cover              | renderer checks dependency availability before calling helper         | -        |
| src/pdf_toolbox/renderers/\_http_util.py:30      | type: ignore[no-untyped-call] | requests call lacks typing information                                | -        |
| src/pdf_toolbox/renderers/http_office.py:23      | pragma: no cover              | optional dependency import guard exercised via unit tests             | -        |
| src/pdf_toolbox/renderers/http_office.py:24      | type: ignore[import-untyped]  | requests library does not ship type information                       | -        |
| src/pdf_toolbox/renderers/http_office.py:25      | pragma: no cover              | gracefully handle missing optional dependency                         | -        |
| src/pdf_toolbox/renderers/http_office.py:26      | type: ignore[assignment]      | sentinel assignment when dependency unavailable                       | -        |
| src/pdf_toolbox/renderers/http_office.py:30      | pragma: no cover              | branch only aids type checking when dependency missing                | -        |
| src/pdf_toolbox/renderers/http_office.py:346     | PLR0913                       | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/lightweight_stub.py:27 | PLR0913                       | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/ms_office.py:19        | pragma: no cover              | PowerPoint automation relies on pywin32                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:20        | type: ignore                  | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:22        | type: ignore                  | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:24        | pragma: no cover              | gracefully degrade without pywin32                                    | -        |
| src/pdf_toolbox/renderers/ms_office.py:25        | type: ignore[assignment]      | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:26        | type: ignore[assignment]      | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:27        | pragma: no cover              | PowerPoint COM only available on Windows                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:28        | type: ignore[assignment]      | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:29        | type: ignore[assignment]      | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:75        | pragma: no cover              | surface COM automation failure                                        | -        |
| src/pdf_toolbox/renderers/ms_office.py:104       | pragma: no cover              | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:134       | pragma: no cover              | propagate PowerPoint open failure                                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:161       | pragma: no cover              | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:175       | pragma: no cover              | guard unexpected COM errors                                           | -        |
| src/pdf_toolbox/renderers/ms_office.py:242       | pragma: no cover              | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/ms_office.py:256       | PLR0913                       | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/ms_office.py:312       | pragma: no cover              | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/pptx.py:57             | PLR0913                       | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/pptx_base.py:22        | PLR0913                       | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/registry.py:83         | BLE001, RUF100                | metadata backends can raise arbitrary errors; degrade to no plugins   | -        |
| src/pdf_toolbox/renderers/registry.py:106        | BLE001, RUF100                | plugin entry point import may fail arbitrarily; degrade to warning    | -        |
| src/pdf_toolbox/renderers/registry.py:125        | BLE001, RUF100                | plugin modules may be missing or broken; degrade to warning           | -        |
| src/pdf_toolbox/renderers/registry.py:174        | BLE001, RUF100                | builtin providers rely on optional platform modules; degrade to debug | -        |
| src/pdf_toolbox/renderers/registry.py:206        | BLE001, RUF100                | renderer constructors may fail arbitrarily; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:247        | BLE001, RUF100                | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:265        | BLE001, RUF100                | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/utils.py:13                      | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/conftest.py:4                              | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/gui/conftest_qt.py:117                     | N802                          | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:120                     | N802, type: ignore[override]  | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:123                     | N802                          | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:126                     | N802                          | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:129                     | N802, type: ignore[override]  | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:132                     | N802, type: ignore[override]  | stub preserves Qt camelCase API                                       | -        |
| tests/gui/conftest_qt.py:172                     | type: ignore[attr-defined]    | PySide6 stubs miss QDialog.Accepted                                   | -        |
| tests/gui/conftest_qt.py:216                     | N802, pragma: no cover        | method name follows Qt worker API                                     | -        |
| tests/gui/test_main_window.py:479                | N802                          | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:493                | type: ignore[assignment]      | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:601                | N802                          | mimic Qt worker API naming                                            | -        |
| tests/gui/test_main_window.py:611                | type: ignore[assignment]      | stub worker lacks QObject base class                                  | -        |
| tests/gui/test_main_window.py:693                | type: ignore[override]        | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:697                | type: ignore[override]        | stub implements abstract renderer for tests                           | -        |
| tests/gui/test_main_window.py:1058               | type: ignore[no-untyped-def]  | Worker injects Event parameter dynamically                            | -        |
| tests/gui/test_main_window.py:1085               | type: ignore[attr-defined]    | fixture injects helper on MainWindow for tests                        | -        |
| tests/gui/test_widgets.py:124                    | N802                          | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:131                    | N802                          | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:142                    | N802                          | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:145                    | N802                          | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:187                    | N802                          | stub mirrors Qt URL API                                               | -        |
| tests/gui/test_widgets.py:194                    | N802                          | stub mirrors Qt MIME API                                              | -        |
| tests/gui/test_widgets.py:204                    | N802                          | stub mirrors Qt event API                                             | -        |
| tests/gui/test_widgets.py:222                    | type: ignore[attr-defined]    | PySide6 stubs miss Qt.LeftButton                                      | -        |
| tests/gui/test_worker.py:40                      | type: ignore[no-untyped-def]  | Worker injects Event parameter dynamically                            | -        |
| tests/renderers/test_http_office.py:219          | type: ignore[import-untyped]  | requests library does not ship type information                       | -        |
| tests/renderers/test_http_office.py:246          | type: ignore[import-untyped]  | requests library does not ship type information                       | -        |
| tests/renderers/test_http_office.py:480          | type: ignore[import-untyped]  | requests library does not ship type information                       | -        |
| tests/test_actions.py:99                         | pragma: no cover              | stub action body unused during registry import                        | -        |
| tests/test_actions.py:101                        | type: ignore[attr-defined]    | mark stub action for registry import                                  | -        |
| tests/test_actions.py:103                        | type: ignore[attr-defined]    | register stub action on module for import test                        | -        |
| tests/test_actions_e2e.py:9                      | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/test_converters.py:3                       | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/test_images.py:6                           | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/test_miro.py:215                           | pragma: no cover              | ensure dummy renderer keeps simple coverage                           | -        |
| tests/test_pptx.py:86                            | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:174                           | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:262                           | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:335                           | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:406                           | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx_e2e.py:9                         | type: ignore                  | PyMuPDF lacks type hints                                              | -        |
| tests/test_pptx_e2e.py:76                        | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_pptx_ms_office_renderer.py:21         | N802                          | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:25         | N802                          | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:46         | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:71         | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:77         | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:90         | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:107        | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:120        | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:125        | N802                          | COM style method name                                                 | -        |
| tests/test_pptx_renderer.py:20                   | PLR0913                       | renderer stub matches renderer API signature                          | -        |
| tests/test_renderer_registry.py:12               | PLR0913                       | renderer API requires many parameters                                 | -        |
| tests/test_utils.py:5                            | type: ignore                  | PyMuPDF lacks type hints                                              | -        |

<!-- mdformat on -->

## Runtime Exceptions

<!-- mdformat off -->

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                    |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx.no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-renderer) |

<!-- mdformat on -->
