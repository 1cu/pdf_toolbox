# Documented Exceptions

| File                                    | Rule                                     | Reason                                              | Issue/PR |
| --------------------------------------- | ---------------------------------------- | --------------------------------------------------- | -------- |
| scripts/check_coverage.py:8             | B405                                     | stdlib XML parser on trusted coverage file          | -        |
| scripts/check_coverage.py:38            | B314                                     | parsing trusted coverage report                     | -        |
| scripts/prune_releases.py:28            | S310                                     | urllib Request for GitHub API                       | -        |
| scripts/prune_releases.py:33            | S310, B310                               | urllib urlopen for GitHub API                       | -        |
| scripts/prune_releases.py:60            | type: ignore[arg-type]                   | GitHub API returns untyped data                     | -        |
| src/pdf_toolbox/__main__.py:5           | pragma: no cover                         | entry point                                         | -        |
| src/pdf_toolbox/actions.py:48           | pragma: no cover                         | trivial helper                                      | -        |
| src/pdf_toolbox/actions.py:89           | type: ignore[attr-defined]               | attach custom attribute for action registry         | -        |
| src/pdf_toolbox/actions.py:137          | pragma: no cover                         | defensive                                           | -        |
| src/pdf_toolbox/actions.py:140          | pragma: no cover                         | defensive                                           | -        |
| src/pdf_toolbox/actions.py:155          | pragma: no cover                         | optional deps                                       | -        |
| src/pdf_toolbox/builtin/__init__.py:25  | pragma: no cover                         | optional dependencies                               | -        |
| src/pdf_toolbox/builtin/docx.py:9       | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/docx.py:43      | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/docx.py:45      | pragma: no cover                         | input PDF in tests has no text                      | -        |
| src/pdf_toolbox/builtin/docx.py:48      | pragma: no cover                         | input PDF in tests has no text                      | -        |
| src/pdf_toolbox/builtin/docx.py:52      | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/docx.py:57      | pragma: no cover                         | rare colorspace                                     | -        |
| src/pdf_toolbox/builtin/docx.py:60      | pragma: no cover                         | rare colorspace                                     | -        |
| src/pdf_toolbox/builtin/extract.py:8    | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/extract.py:42   | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/extract.py:51   | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/extract.py:72   | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/extract.py:82   | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/images.py:11    | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/images.py:68    | PLR0913, PLR0912, PLR0915                | rendering pages needs many parameters and branches  | -        |
| src/pdf_toolbox/builtin/images.py:131   | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/images.py:144   | pragma: no cover                         | exotic colorspace                                   | -        |
| src/pdf_toolbox/builtin/images.py:148   | pragma: no cover                         | rare alpha channel                                  | -        |
| src/pdf_toolbox/builtin/images.py:290   | PLR0913                                  | conversion helper requires many parameters          | -        |
| src/pdf_toolbox/builtin/optimise.py:20  | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/optimise.py:65  | type: ignore[assignment]                 | PyMuPDF page typing mismatch                        | -        |
| src/pdf_toolbox/builtin/optimise.py:68  | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/optimise.py:72  | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/optimise.py:98  | PLR0913                                  | optimisation API exposes many options               | -        |
| src/pdf_toolbox/builtin/optimise.py:163 | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/optimise.py:179 | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/optimise.py:227 | PLR0913                                  | batch optimisation needs several arguments          | -        |
| src/pdf_toolbox/builtin/optimise.py:254 | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/repair.py:25    | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/repair.py:33    | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/unlock.py:8     | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/builtin/unlock.py:32    | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/builtin/unlock.py:42    | pragma: no cover                         | cooperative cancellation guard                      | -        |
| src/pdf_toolbox/gui/__init__.py:44      | pragma: no cover                         | environment dependent                               | -        |
| src/pdf_toolbox/gui/__init__.py:49      | pragma: no cover                         | entry point                                         | -        |
| src/pdf_toolbox/gui/__main__.py:5       | pragma: no cover                         | entry point                                         | -        |
| src/pdf_toolbox/gui/main_window.py:51   | pragma: no cover                         | exercised in GUI tests                              | -        |
| src/pdf_toolbox/gui/main_window.py:54   | PLR0915                                  | constructor sets up many widgets                    | -        |
| src/pdf_toolbox/gui/main_window.py:107  | type: ignore[attr-defined]               | PySide6 stubs miss form layout policy enum          | -        |
| src/pdf_toolbox/gui/main_window.py:130  | type: ignore[attr-defined]               | PySide6 stubs miss tool button enum                 | -        |
| src/pdf_toolbox/gui/main_window.py:161  | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:167  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:169  | type: ignore[attr-defined]               | PySide6 stubs miss Qt.UserRole                      | -        |
| src/pdf_toolbox/gui/main_window.py:175  | PLR0912, PLR0915                         | dynamic form builder is inherently complex          | -        |
| src/pdf_toolbox/gui/main_window.py:194  | type: ignore[attr-defined]               | `types.UnionType` absent from stubs                 | -        |
| src/pdf_toolbox/gui/main_window.py:277  | type: ignore[arg-type]                   | PySide6 stubs reject tuple variant                  | -        |
| src/pdf_toolbox/gui/main_window.py:280  | PLR0912                                  | argument collection involves many branches          | -        |
| src/pdf_toolbox/gui/main_window.py:295  | type: ignore[attr-defined]               | PySide6 stubs miss Qt enum                          | -        |
| src/pdf_toolbox/gui/main_window.py:349  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:366  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:400  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:441  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:457  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:472  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:481  | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:485  | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:492  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:501  | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:505  | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:513  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/main_window.py:525  | type: ignore[attr-defined]               | PySide6 stubs miss dialog button enum               | -        |
| src/pdf_toolbox/gui/main_window.py:529  | type: ignore[attr-defined]               | PySide6 stubs miss dialog attribute                 | -        |
| src/pdf_toolbox/gui/main_window.py:550  | pragma: no cover                         | GUI handler                                         | -        |
| src/pdf_toolbox/gui/widgets.py:17       | pragma: no cover                         | GUI helper                                          | -        |
| src/pdf_toolbox/gui/widgets.py:38       | type: ignore[override], pragma: no cover | override signal emitter with broader type; GUI-only | -        |
| src/pdf_toolbox/gui/widgets.py:43       | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:78       | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:83       | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/widgets.py:96       | pragma: no cover                         | GUI widget                                          | -        |
| src/pdf_toolbox/gui/widgets.py:101      | N802                                     | Qt requires camelCase event name                    | -        |
| src/pdf_toolbox/gui/worker.py:11        | pragma: no cover                         | thread/GUI                                          | -        |
| src/pdf_toolbox/i18n.py:39              | pragma: no cover                         | env-dependent                                       | -        |
| src/pdf_toolbox/i18n.py:62              | pragma: no cover                         | defensive                                           | -        |
| src/pdf_toolbox/i18n.py:75              | pragma: no cover                         | defensive                                           | -        |
| src/pdf_toolbox/utils.py:13             | type: ignore                             | PyMuPDF lacks type hints                            | -        |
| src/pdf_toolbox/utils.py:96             | pragma: no cover                         | best effort                                         | -        |
| src/pdf_toolbox/utils.py:179            | pragma: no cover                         | cooperative cancellation helper                     | -        |
| src/pdf_toolbox/utils.py:200            | pragma: no cover                         | best effort                                         | -        |
| src/pdf_toolbox/utils.py:216            | pragma: no cover                         | best effort                                         | -        |
