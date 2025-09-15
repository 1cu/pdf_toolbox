# Documented Exceptions

| File                                       | Rule                                     | Reason                                              | Issue/PR |
| ------------------------------------------ | ---------------------------------------- | --------------------------------------------------- | -------- |
| scripts/check_coverage.py:8                | B405                                     | stdlib XML parser on trusted coverage file          | -        |
| scripts/check_coverage.py:38               | B314                                     | parsing trusted coverage report                     | -        |
| scripts/generate_exception_overview.py:23  | PLR0912                                  | parsing requires several branches                   | -        |
| scripts/prune_releases.py:28               | S310                                     | urllib Request for GitHub API                       | -        |
| scripts/prune_releases.py:33               | S310, B310                               | urllib urlopen for GitHub API                       | -        |
| scripts/prune_releases.py:60               | type: ignore[arg-type]                   | GitHub API returns untyped data                     | -        |
| src/pdf_toolbox/actions/__init__.py:87     | type: ignore[attr-defined]               | attach custom attribute for action registration     | -        |
| src/pdf_toolbox/actions/docx.py:9          | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/actions/extract.py:8       | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/actions/images.py:11       | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/actions/images.py:120      | PLR0913, PLR0912, PLR0915                | rendering pages needs many parameters and branches  | -        |
| src/pdf_toolbox/actions/images.py:304      | PLR0913                                  | conversion helper requires many parameters          | -        |
| src/pdf_toolbox/actions/optimise.py:20     | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/actions/optimise.py:65     | type: ignore[assignment]                 | PyMuPDF page typing mismatch                        | -        |
| src/pdf_toolbox/actions/optimise.py:94     | PLR0913                                  | optimisation API exposes many options               | -        |
| src/pdf_toolbox/actions/optimise.py:221    | PLR0913                                  | batch optimisation needs several arguments          | -        |
| src/pdf_toolbox/actions/pptx.py:110        | PLR0913                                  | action interface requires many parameters           | -        |
| src/pdf_toolbox/actions/unlock.py:8        | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/gui/__init__.py:44         | pragma: no cover                         | environment dependent                               | -        |
| src/pdf_toolbox/gui/main_window.py:55      | PLR0915                                  | constructor sets up many widgets                    | -        |
| src/pdf_toolbox/gui/main_window.py:108     | type: ignore[attr-defined]               | PySide6 stubs miss form layout policy enum          | -        |
| src/pdf_toolbox/gui/main_window.py:144     | type: ignore[attr-defined]               | PySide6 stubs miss tool button enum                 | -        |
| src/pdf_toolbox/gui/main_window.py:175     | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:181     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:183     | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:189     | PLR0912, PLR0915                         | dynamic form builder is inherently complex          | -        |
| src/pdf_toolbox/gui/main_window.py:208     | type: ignore[attr-defined]               | `types.UnionType` absent from stubs                 | -        |
| src/pdf_toolbox/gui/main_window.py:305     | type: ignore[arg-type]                   | PySide6 stubs reject tuple variant                  | -        |
| src/pdf_toolbox/gui/main_window.py:308     | PLR0912                                  | argument collection involves many branches          | -        |
| src/pdf_toolbox/gui/main_window.py:323     | type: ignore[attr-defined]               | PySide6 stubs miss Qt enum                          | -        |
| src/pdf_toolbox/gui/main_window.py:377     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:394     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:428     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:469     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:485     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:500     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:509     | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:513     | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:520     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:529     | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:533     | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:541     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:553     | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:557     | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:578     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:593     | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:597     | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:607     | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/widgets.py:17          | pragma: no cover                         | GUI helper                                          | -        |
| src/pdf_toolbox/gui/widgets.py:38          | type: ignore[override], pragma: no cover | override signal emitter with broader type; GUI-only | -        |
| src/pdf_toolbox/gui/widgets.py:43          | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:78          | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:83          | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:96          | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:101         | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/worker.py:11           | pragma: no cover                         | thread/GUI                                          | -        |
| src/pdf_toolbox/renderers/ms_office.py:12  | pragma: no cover                         | Windows-only COM modules                            | -        |
| src/pdf_toolbox/renderers/ms_office.py:13  | type: ignore                             | pywin32 missing on non-Windows                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:14  | type: ignore                             | pywin32 missing on non-Windows                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:15  | pragma: no cover                         | gracefully handle missing COM                       | -        |
| src/pdf_toolbox/renderers/ms_office.py:16  | type: ignore                             | indicate COM unavailability                         | -        |
| src/pdf_toolbox/renderers/ms_office.py:42  | pragma: no cover                         | relies on PowerPoint COM                            | -        |
| src/pdf_toolbox/renderers/ms_office.py:53  | pragma: no cover                         | PowerPoint COM cleanup                              | -        |
| src/pdf_toolbox/renderers/ms_office.py:61  | pragma: no cover                         | PowerPoint COM                                      | -        |
| src/pdf_toolbox/renderers/ms_office.py:118 | pragma: no cover                         | COM export failures                                 | -        |
| src/pdf_toolbox/renderers/ms_office.py:125 | PLR0913                                  | renderer API requires many parameters               | -        |
| src/pdf_toolbox/renderers/ms_office.py:167 | pragma: no cover                         | COM export failures                                 | -        |
| src/pdf_toolbox/renderers/pptx.py:21       | PLR0913                                  | renderer API requires many parameters               | -        |
| src/pdf_toolbox/renderers/pptx.py:48       | PLR0913                                  | renderer API requires many parameters               | -        |
| src/pdf_toolbox/utils.py:13                | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/conftest.py:3                        | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_batch_optimise.py:3             | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_converters.py:3                 | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise.py:3                   | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise.py:50                  | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise_extra.py:5             | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise_progress.py:3          | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_pptx.py:99                      | PLR0913                                  | renderer API requires many parameters               | -        |
| tests/test_pptx.py:141                     | PLR0913                                  | renderer API requires many parameters               | -        |
| tests/test_utils.py:5                      | type: ignore                             | PyMuPDF lacks type hints                            | -        |
