# Documented Exceptions

| File                                      | Rule                                     | Reason                                              | Issue/PR |
| ----------------------------------------- | ---------------------------------------- | --------------------------------------------------- | -------- |
| scripts/check_coverage.py:8               | B405                                     | stdlib XML parser on trusted coverage file          | -        |
| scripts/check_coverage.py:38              | B314                                     | parsing trusted coverage report                     | -        |
| scripts/generate_exception_overview.py:21 | PLR0912                                  | parsing requires several branches                   | -        |
| scripts/prune_releases.py:28              | S310                                     | urllib Request for GitHub API                       | -        |
| scripts/prune_releases.py:33              | S310, B310                               | urllib urlopen for GitHub API                       | -        |
| scripts/prune_releases.py:60              | type: ignore[arg-type]                   | GitHub API returns untyped data                     | -        |
| src/pdf_toolbox/actions.py:89             | type: ignore[attr-defined]               | attach custom attribute for action registry         | -        |
| src/pdf_toolbox/builtin/docx.py:9         | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/extract.py:8      | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/images.py:11      | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/images.py:68      | PLR0913, PLR0912, PLR0915                | rendering pages needs many parameters and branches  | -        |
| src/pdf_toolbox/builtin/images.py:283     | PLR0913                                  | conversion helper requires many parameters          | -        |
| src/pdf_toolbox/builtin/optimise.py:20    | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/optimise.py:65    | type: ignore[assignment]                 | PyMuPDF page typing mismatch                        | -        |
| src/pdf_toolbox/builtin/optimise.py:94    | PLR0913                                  | optimisation API exposes many options               | -        |
| src/pdf_toolbox/builtin/optimise.py:221   | PLR0913                                  | batch optimisation needs several arguments          | -        |
| src/pdf_toolbox/builtin/unlock.py:8       | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/gui/__init__.py:44        | pragma: no cover                         | environment dependent                               | -        |
| src/pdf_toolbox/gui/main_window.py:52     | PLR0915                                  | constructor sets up many widgets                    | -        |
| src/pdf_toolbox/gui/main_window.py:105    | type: ignore[attr-defined]               | PySide6 stubs miss form layout policy enum          | -        |
| src/pdf_toolbox/gui/main_window.py:128    | type: ignore[attr-defined]               | PySide6 stubs miss tool button enum                 | -        |
| src/pdf_toolbox/gui/main_window.py:159    | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:165    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:167    | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:173    | PLR0912, PLR0915                         | dynamic form builder is inherently complex          | -        |
| src/pdf_toolbox/gui/main_window.py:192    | type: ignore[attr-defined]               | `types.UnionType` absent from stubs                 | -        |
| src/pdf_toolbox/gui/main_window.py:275    | type: ignore[arg-type]                   | PySide6 stubs reject tuple variant                  | -        |
| src/pdf_toolbox/gui/main_window.py:278    | PLR0912                                  | argument collection involves many branches          | -        |
| src/pdf_toolbox/gui/main_window.py:293    | type: ignore[attr-defined]               | PySide6 stubs miss Qt enum                          | -        |
| src/pdf_toolbox/gui/main_window.py:347    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:364    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:398    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:439    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:455    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:470    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:479    | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:483    | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:490    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:499    | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:503    | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:511    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:523    | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:527    | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:548    | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/widgets.py:17         | pragma: no cover                         | GUI helper                                          | -        |
| src/pdf_toolbox/gui/widgets.py:38         | type: ignore[override], pragma: no cover | override signal emitter with broader type; GUI-only | -        |
| src/pdf_toolbox/gui/widgets.py:43         | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:78         | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:83         | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:96         | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:101        | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/worker.py:11          | pragma: no cover                         | thread/GUI                                          | -        |
| src/pdf_toolbox/utils.py:13               | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/conftest.py:3                       | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_batch_optimise.py:3            | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_converters.py:3                | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise.py:3                  | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise.py:50                 | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise_extra.py:5            | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_optimise_progress.py:3         | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| tests/test_utils.py:5                     | type: ignore                             | PyMuPDF lacks type hints                            | -        |
