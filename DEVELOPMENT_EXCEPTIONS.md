# Documented Exceptions

| File                                             | Rule                                     | Reason                                                 | Issue/PR |
| ------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------ | -------- |
| scripts/check_coverage.py:8                      | B405                                     | stdlib XML parser on trusted coverage file             | -        |
| scripts/check_coverage.py:38                     | B314                                     | parsing trusted coverage report                        | -        |
| scripts/generate_exception_overview.py:51        | PLR0912                                  | parsing requires several branches                      | -        |
| scripts/prune_releases.py:28                     | S310                                     | urllib Request for GitHub API                          | -        |
| scripts/prune_releases.py:33                     | S310, B310                               | urllib urlopen for GitHub API                          | -        |
| scripts/prune_releases.py:60                     | type: ignore[arg-type]                   | GitHub API returns untyped data                        | -        |
| src/pdf_toolbox/actions/__init__.py:87           | type: ignore[attr-defined]               | attach renderer flag for GUI                           | -        |
| src/pdf_toolbox/actions/__init__.py:94           | type: ignore[attr-defined]               | attach custom attribute for action registration        | -        |
| src/pdf_toolbox/actions/extract.py:8             | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| src/pdf_toolbox/actions/miro.py:27               | PLR0913                                  | action signature mirrors GUI form                      | -        |
| src/pdf_toolbox/actions/pdf_images.py:11         | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| src/pdf_toolbox/actions/pdf_images.py:127        | PLR0913, PLR0912, PLR0915                | rendering pages needs many parameters and branches     | -        |
| src/pdf_toolbox/actions/pdf_images.py:322        | PLR0913                                  | conversion helper requires many parameters             | -        |
| src/pdf_toolbox/actions/pptx.py:19               | PLR0913                                  | action interface requires many parameters              | -        |
| src/pdf_toolbox/actions/unlock.py:8              | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| src/pdf_toolbox/gui/__init__.py:44               | pragma: no cover                         | environment dependent                                  | -        |
| src/pdf_toolbox/gui/main_window.py:86            | PLR0915                                  | constructor sets up many widgets                       | -        |
| src/pdf_toolbox/gui/main_window.py:164           | type: ignore[attr-defined]               | PySide6 stubs miss form layout policy enum             | -        |
| src/pdf_toolbox/gui/main_window.py:200           | type: ignore[attr-defined]               | PySide6 stubs miss tool button enum                    | -        |
| src/pdf_toolbox/gui/main_window.py:231           | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                         | -        |
| src/pdf_toolbox/gui/main_window.py:237           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:239           | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                         | -        |
| src/pdf_toolbox/gui/main_window.py:245           | PLR0912, PLR0915                         | dynamic form builder is inherently complex             | -        |
| src/pdf_toolbox/gui/main_window.py:303           | type: ignore[attr-defined]               | `types.UnionType` absent from stubs                    | -        |
| src/pdf_toolbox/gui/main_window.py:403           | type: ignore[arg-type]                   | PySide6 stubs reject tuple variant                     | -        |
| src/pdf_toolbox/gui/main_window.py:404           | type: ignore[assignment]                 | tuple already handled                                  | -        |
| src/pdf_toolbox/gui/main_window.py:413           | PLR0912                                  | argument collection involves many branches             | -        |
| src/pdf_toolbox/gui/main_window.py:428           | type: ignore[attr-defined]               | PySide6 stubs miss Qt enum                             | -        |
| src/pdf_toolbox/gui/main_window.py:491           | pragma: no cover                         | opens external documentation                           | -        |
| src/pdf_toolbox/gui/main_window.py:535           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:552           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:586           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:613           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:657           | N802                                     | Qt requires camelCase event name                       | -        |
| src/pdf_toolbox/gui/main_window.py:660           | pragma: no cover                         | ensure worker shutdown on close                        | -        |
| src/pdf_toolbox/gui/main_window.py:668           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:683           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:692           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                  | -        |
| src/pdf_toolbox/gui/main_window.py:696           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                    | -        |
| src/pdf_toolbox/gui/main_window.py:703           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:712           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                  | -        |
| src/pdf_toolbox/gui/main_window.py:716           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                    | -        |
| src/pdf_toolbox/gui/main_window.py:724           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:736           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                  | -        |
| src/pdf_toolbox/gui/main_window.py:740           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                    | -        |
| src/pdf_toolbox/gui/main_window.py:763           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/main_window.py:793           | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum                  | -        |
| src/pdf_toolbox/gui/main_window.py:797           | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                    | -        |
| src/pdf_toolbox/gui/main_window.py:804           | pragma: no cover                         | GUI handler                                            | -        |
| src/pdf_toolbox/gui/widgets.py:17                | pragma: no cover                         | GUI helper                                             | -        |
| src/pdf_toolbox/gui/widgets.py:38                | type: ignore[override], pragma: no cover | override signal emitter with broader type; GUI-only    | -        |
| src/pdf_toolbox/gui/widgets.py:43                | pragma: no cover                         | GUI widget                                             | -        |
| src/pdf_toolbox/gui/widgets.py:78                | N802                                     | Qt requires camelCase event name                       | -        |
| src/pdf_toolbox/gui/widgets.py:83                | N802                                     | Qt requires camelCase event name                       | -        |
| src/pdf_toolbox/gui/widgets.py:96                | pragma: no cover                         | GUI widget                                             | -        |
| src/pdf_toolbox/gui/widgets.py:101               | N802                                     | Qt requires camelCase event name                       | -        |
| src/pdf_toolbox/gui/worker.py:11                 | pragma: no cover                         | thread/GUI                                             | -        |
| src/pdf_toolbox/image_utils.py:8                 | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| src/pdf_toolbox/miro.py:13                       | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| src/pdf_toolbox/miro.py:245                      | pragma: no cover                         | guard against environment-specific WebP encoder issues | -        |
| src/pdf_toolbox/miro.py:260                      | pragma: no cover                         | Pillow sometimes lacks WebP support                    | -        |
| src/pdf_toolbox/miro.py:280                      | pragma: no cover                         | PNG encoder failure varies by platform                 | -        |
| src/pdf_toolbox/miro.py:300                      | pragma: no cover                         | JPEG encoder may be unavailable                        | -        |
| src/pdf_toolbox/miro.py:693                      | pragma: no cover                         | keep GUI responsive despite renderer crashes           | -        |
| src/pdf_toolbox/renderers/lightweight_stub.py:27 | PLR0913                                  | renderer API requires many parameters                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:19        | pragma: no cover                         | PowerPoint automation relies on pywin32                | -        |
| src/pdf_toolbox/renderers/ms_office.py:20        | type: ignore                             | pywin32 is optional and lacks type hints               | -        |
| src/pdf_toolbox/renderers/ms_office.py:22        | type: ignore                             | pywin32 is optional and lacks type hints               | -        |
| src/pdf_toolbox/renderers/ms_office.py:24        | pragma: no cover                         | gracefully degrade without pywin32                     | -        |
| src/pdf_toolbox/renderers/ms_office.py:25        | type: ignore[assignment]                 | treat missing pywin32 as absent backend                | -        |
| src/pdf_toolbox/renderers/ms_office.py:26        | type: ignore[assignment]                 | treat missing pywin32 as absent backend                | -        |
| src/pdf_toolbox/renderers/ms_office.py:27        | pragma: no cover                         | PowerPoint COM only available on Windows               | -        |
| src/pdf_toolbox/renderers/ms_office.py:28        | type: ignore[assignment]                 | COM unsupported on non-Windows platforms               | -        |
| src/pdf_toolbox/renderers/ms_office.py:29        | type: ignore[assignment]                 | COM unsupported on non-Windows platforms               | -        |
| src/pdf_toolbox/renderers/ms_office.py:75        | pragma: no cover                         | surface COM automation failure                         | -        |
| src/pdf_toolbox/renderers/ms_office.py:104       | pragma: no cover                         | propagate COM initialisation failure                   | -        |
| src/pdf_toolbox/renderers/ms_office.py:134       | pragma: no cover                         | propagate PowerPoint open failure                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:161       | pragma: no cover                         | propagate COM initialisation failure                   | -        |
| src/pdf_toolbox/renderers/ms_office.py:175       | pragma: no cover                         | guard unexpected COM errors                            | -        |
| src/pdf_toolbox/renderers/ms_office.py:242       | pragma: no cover                         | propagate COM export failure                           | -        |
| src/pdf_toolbox/renderers/ms_office.py:256       | PLR0913                                  | renderer API requires many parameters                  | -        |
| src/pdf_toolbox/renderers/ms_office.py:312       | pragma: no cover                         | propagate COM export failure                           | -        |
| src/pdf_toolbox/renderers/pptx.py:60             | PLR0913                                  | renderer API requires many parameters                  | -        |
| src/pdf_toolbox/renderers/pptx_base.py:16        | PLR0913                                  | renderer API requires many parameters                  | -        |
| src/pdf_toolbox/renderers/registry.py:160        | pragma: no cover                         | unreachable once select(strict=True) succeeds          | -        |
| src/pdf_toolbox/utils.py:13                      | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| tests/conftest.py:3                              | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| tests/test_actions.py:99                         | pragma: no cover                         | stub action body unused during registry import         | -        |
| tests/test_actions.py:101                        | type: ignore[attr-defined]               | mark stub action for registry import                   | -        |
| tests/test_actions.py:103                        | type: ignore[attr-defined]               | register stub action on module for import test         | -        |
| tests/test_converters.py:3                       | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| tests/test_images.py:6                           | type: ignore                             | PyMuPDF lacks type hints                               | -        |
| tests/test_miro.py:215                           | pragma: no cover                         | ensure dummy renderer keeps simple coverage            | -        |
| tests/test_pptx.py:96                            | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_pptx.py:184                           | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_pptx.py:272                           | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_pptx.py:345                           | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_pptx.py:416                           | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_pptx_ms_office_renderer.py:21         | N802                                     | mirror COM method name                                 | -        |
| tests/test_pptx_ms_office_renderer.py:25         | N802                                     | mirror COM method name                                 | -        |
| tests/test_pptx_ms_office_renderer.py:46         | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:71         | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:77         | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:90         | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:107        | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:120        | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_ms_office_renderer.py:125        | N802                                     | COM style method name                                  | -        |
| tests/test_pptx_renderer.py:19                   | PLR0913                                  | renderer stub matches renderer API signature           | -        |
| tests/test_renderer_registry.py:12               | PLR0913                                  | renderer API requires many parameters                  | -        |
| tests/test_utils.py:5                            | type: ignore                             | PyMuPDF lacks type hints                               | -        |

## Runtime Exceptions

| Exception                                               | Message key      | Locales                                                                      | Docs                                                                                                               |
| ------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| pdf_toolbox.renderers.pptx.PptxProviderUnavailableError | pptx_no_provider | [en](src/pdf_toolbox/locales/en.json), [de](src/pdf_toolbox/locales/de.json) | [PPTX_PROVIDER_DOCS_URL](https://github.com/1cu/pdf_toolbox/blob/main/docs/adr/0001-pptx-provider-architecture.md) |
