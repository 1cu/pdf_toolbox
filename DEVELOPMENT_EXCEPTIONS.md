# Documented Exceptions

<!-- mdformat off -->

| File                                             | Rule                                     | Reason                                                                | Issue/PR |
| ------------------------------------------------ | ---------------------------------------- | --------------------------------------------------------------------- | -------- |
| scripts/check_coverage.py:8                      | B405                                     | stdlib XML parser on trusted coverage file                            | -        |
| scripts/check_coverage.py:38                     | B314                                     | parsing trusted coverage report                                       | -        |
| scripts/generate_exception_overview.py:53        | PLR0912                                  | parsing requires several branches                                     | -        |
| scripts/prune_releases.py:28                     | S310                                     | urllib Request for GitHub API                                         | -        |
| scripts/prune_releases.py:33                     | S310, B310                               | urllib urlopen for GitHub API                                         | -        |
| scripts/prune_releases.py:60                     | type: ignore[arg-type]                   | GitHub API returns untyped data                                       | -        |
| src/pdf_toolbox/actions/\_\_init\_\_.py:87       | type: ignore[attr-defined]               | attach renderer flag for GUI                                          | -        |
| src/pdf_toolbox/actions/\_\_init\_\_.py:94       | type: ignore[attr-defined]               | attach custom attribute for action registration                       | -        |
| src/pdf_toolbox/actions/extract.py:8             | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/actions/miro.py:27               | PLR0913                                  | action signature mirrors GUI form                                     | -        |
| src/pdf_toolbox/actions/pdf_images.py:11         | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/actions/pdf_images.py:127        | PLR0913, PLR0912, PLR0915                | rendering pages needs many parameters and branches                    | -        |
| src/pdf_toolbox/actions/pdf_images.py:322        | PLR0913                                  | conversion helper requires many parameters                            | -        |
| src/pdf_toolbox/actions/pptx.py:19               | PLR0913                                  | action interface requires many parameters                             | -        |
| src/pdf_toolbox/actions/unlock.py:8              | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/gui/\_\_init\_\_.py:44           | pragma: no cover                         | environment dependent                                                 | -        |
| src/pdf_toolbox/gui/main_window.py:87            | PLR0915                                  | constructor sets up many widgets                                      | -        |
| src/pdf_toolbox/gui/main_window.py:165           | type: ignore[attr-defined]               | PySide6 stubs miss form layout policy enum                            | -        |
| src/pdf_toolbox/gui/main_window.py:201           | type: ignore[attr-defined]               | PySide6 stubs miss tool button enum                                   | -        |
| src/pdf_toolbox/gui/main_window.py:232           | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                                        | -        |
| src/pdf_toolbox/gui/main_window.py:238           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:240           | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                                        | -        |
| src/pdf_toolbox/gui/main_window.py:246           | PLR0912, PLR0915                         | dynamic form builder is inherently complex                            | -        |
| src/pdf_toolbox/gui/main_window.py:304           | type: ignore[attr-defined]               | `types.UnionType` absent from stubs                                   | -        |
| src/pdf_toolbox/gui/main_window.py:404           | type: ignore[arg-type]                   | PySide6 stubs reject tuple variant                                    | -        |
| src/pdf_toolbox/gui/main_window.py:405           | type: ignore[assignment]                 | tuple already handled                                                 | -        |
| src/pdf_toolbox/gui/main_window.py:414           | PLR0912                                  | argument collection involves many branches                            | -        |
| src/pdf_toolbox/gui/main_window.py:429           | type: ignore[attr-defined]               | PySide6 stubs miss Qt enum                                            | -        |
| src/pdf_toolbox/gui/main_window.py:492           | pragma: no cover                         | opens external documentation                                          | -        |
| src/pdf_toolbox/gui/main_window.py:541           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:558           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:606           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:633           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:677           | N802                                     | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/main_window.py:680           | pragma: no cover                         | ensure worker shutdown on close                                       | -        |
| src/pdf_toolbox/gui/main_window.py:688           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:703           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:712           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:716           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:723           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:732           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:736           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:744           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:756           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:760           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:783           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/main_window.py:812           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                                 | -        |
| src/pdf_toolbox/gui/main_window.py:816           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                                   | -        |
| src/pdf_toolbox/gui/main_window.py:823           | pragma: no cover                         | GUI handler                                                           | -        |
| src/pdf_toolbox/gui/widgets.py:17                | pragma: no cover                         | GUI helper                                                            | -        |
| src/pdf_toolbox/gui/widgets.py:38                | type: ignore[override], pragma: no cover | override signal emitter with broader type; GUI-only                   | -        |
| src/pdf_toolbox/gui/widgets.py:43                | pragma: no cover                         | GUI widget                                                            | -        |
| src/pdf_toolbox/gui/widgets.py:78                | N802                                     | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:83                | N802                                     | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/widgets.py:96                | pragma: no cover                         | GUI widget                                                            | -        |
| src/pdf_toolbox/gui/widgets.py:101               | N802                                     | Qt requires camelCase event name                                      | -        |
| src/pdf_toolbox/gui/worker.py:11                 | pragma: no cover                         | thread/GUI                                                            | -        |
| src/pdf_toolbox/image_utils.py:8                 | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/miro.py:13                       | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| src/pdf_toolbox/miro.py:245                      | pragma: no cover                         | guard against environment-specific WebP encoder issues                | -        |
| src/pdf_toolbox/miro.py:260                      | pragma: no cover                         | Pillow sometimes lacks WebP support                                   | -        |
| src/pdf_toolbox/miro.py:280                      | pragma: no cover                         | PNG encoder failure varies by platform                                | -        |
| src/pdf_toolbox/miro.py:300                      | pragma: no cover                         | JPEG encoder may be unavailable                                       | -        |
| src/pdf_toolbox/miro.py:693                      | pragma: no cover                         | keep GUI responsive despite renderer crashes                          | -        |
| src/pdf_toolbox/renderers/\_http_util.py:8       | pragma: no cover                         | optional dependency import guard exercised via unit tests             | -        |
| src/pdf_toolbox/renderers/\_http_util.py:9       | type: ignore[import-untyped]             | requests library does not ship type information                       | -        |
| src/pdf_toolbox/renderers/\_http_util.py:10      | pragma: no cover                         | gracefully handle missing optional dependency                         | -        |
| src/pdf_toolbox/renderers/\_http_util.py:11      | type: ignore[assignment]                 | sentinel assignment when dependency unavailable                       | -        |
| src/pdf_toolbox/renderers/\_http_util.py:26      | pragma: no cover                         | renderer checks dependency availability before calling helper         | -        |
| src/pdf_toolbox/renderers/\_http_util.py:30      | type: ignore[no-untyped-call]            | requests call lacks typing information                                | -        |
| src/pdf_toolbox/renderers/http_office.py:23      | pragma: no cover                         | optional dependency import guard exercised via unit tests             | -        |
| src/pdf_toolbox/renderers/http_office.py:24      | type: ignore[import-untyped]             | requests library does not ship type information                       | -        |
| src/pdf_toolbox/renderers/http_office.py:25      | pragma: no cover                         | gracefully handle missing optional dependency                         | -        |
| src/pdf_toolbox/renderers/http_office.py:26      | type: ignore[assignment]                 | sentinel assignment when dependency unavailable                       | -        |
| src/pdf_toolbox/renderers/http_office.py:30      | pragma: no cover                         | branch only aids type checking when dependency missing                | -        |
| src/pdf_toolbox/renderers/http_office.py:346     | PLR0913                                  | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/lightweight_stub.py:27 | PLR0913                                  | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/ms_office.py:19        | pragma: no cover                         | PowerPoint automation relies on pywin32                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:20        | type: ignore                             | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:22        | type: ignore                             | pywin32 is optional and lacks type hints                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:24        | pragma: no cover                         | gracefully degrade without pywin32                                    | -        |
| src/pdf_toolbox/renderers/ms_office.py:25        | type: ignore[assignment]                 | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:26        | type: ignore[assignment]                 | treat missing pywin32 as absent backend                               | -        |
| src/pdf_toolbox/renderers/ms_office.py:27        | pragma: no cover                         | PowerPoint COM only available on Windows                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:28        | type: ignore[assignment]                 | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:29        | type: ignore[assignment]                 | COM unsupported on non-Windows platforms                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:75        | pragma: no cover                         | surface COM automation failure                                        | -        |
| src/pdf_toolbox/renderers/ms_office.py:104       | pragma: no cover                         | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:134       | pragma: no cover                         | propagate PowerPoint open failure                                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:161       | pragma: no cover                         | propagate COM initialisation failure                                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:175       | pragma: no cover                         | guard unexpected COM errors                                           | -        |
| src/pdf_toolbox/renderers/ms_office.py:242       | pragma: no cover                         | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/ms_office.py:256       | PLR0913                                  | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/ms_office.py:312       | pragma: no cover                         | propagate COM export failure                                          | -        |
| src/pdf_toolbox/renderers/pptx.py:57             | PLR0913                                  | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/pptx_base.py:22        | PLR0913                                  | renderer API requires many parameters                                 | -        |
| src/pdf_toolbox/renderers/registry.py:83         | BLE001, RUF100                           | metadata backends can raise arbitrary errors; degrade to no plugins   | -        |
| src/pdf_toolbox/renderers/registry.py:106        | BLE001, RUF100                           | plugin entry point import may fail arbitrarily; degrade to warning    | -        |
| src/pdf_toolbox/renderers/registry.py:125        | BLE001, RUF100                           | plugin modules may be missing or broken; degrade to warning           | -        |
| src/pdf_toolbox/renderers/registry.py:174        | BLE001, RUF100                           | builtin providers rely on optional platform modules; degrade to debug | -        |
| src/pdf_toolbox/renderers/registry.py:206        | BLE001, RUF100                           | renderer constructors may fail arbitrarily; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:247        | BLE001, RUF100                           | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/renderers/registry.py:265        | BLE001, RUF100                           | plugin can_handle implementations may fail; treat as unavailable      | -        |
| src/pdf_toolbox/utils.py:13                      | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| tests/conftest.py:3                              | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| tests/renderers/test_http_office.py:219          | type: ignore[import-untyped]             | requests library does not ship type information                       | -        |
| tests/renderers/test_http_office.py:246          | type: ignore[import-untyped]             | requests library does not ship type information                       | -        |
| tests/renderers/test_http_office.py:480          | type: ignore[import-untyped]             | requests library does not ship type information                       | -        |
| tests/test_actions.py:99                         | pragma: no cover                         | stub action body unused during registry import                        | -        |
| tests/test_actions.py:101                        | type: ignore[attr-defined]               | mark stub action for registry import                                  | -        |
| tests/test_actions.py:103                        | type: ignore[attr-defined]               | register stub action on module for import test                        | -        |
| tests/test_converters.py:3                       | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| tests/test_images.py:6                           | type: ignore                             | PyMuPDF lacks type hints                                              | -        |
| tests/test_miro.py:215                           | pragma: no cover                         | ensure dummy renderer keeps simple coverage                           | -        |
| tests/test_pptx.py:98                            | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:186                           | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:274                           | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:347                           | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_pptx.py:418                           | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_pptx_ms_office_renderer.py:21         | N802                                     | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:25         | N802                                     | mirror COM method name                                                | -        |
| tests/test_pptx_ms_office_renderer.py:46         | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:71         | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:77         | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:90         | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:107        | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:120        | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_ms_office_renderer.py:125        | N802                                     | COM style method name                                                 | -        |
| tests/test_pptx_renderer.py:20                   | PLR0913                                  | renderer stub matches renderer API signature                          | -        |
| tests/test_renderer_registry.py:12               | PLR0913                                  | renderer API requires many parameters                                 | -        |
| tests/test_utils.py:5                            | type: ignore                             | PyMuPDF lacks type hints                                              | -        |

<!-- mdformat on -->

## Runtime Exceptions

<!-- mdformat off -->

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                    |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx.no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-renderer) |

<!-- mdformat on -->
