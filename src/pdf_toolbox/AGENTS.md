# Agent Rules for `src/pdf_toolbox`

Follow the repository-wide [AGENTS.md](../../AGENTS.md). Additions for the
package source live here.

## Structure the code

- Use absolute imports within the package.
- Keep modules typed; add annotations to public functions, methods, and return
  values.
- Document public APIs with concise docstrings that IDEs can surface. No Sphinx
  directives are required.
- Place reusable business logic in plain modules so tests can cover it without
  the GUI.

## Integrate with the GUI and actions

- Register new user-facing operations with the `@action` decorator so the GUI can
  discover them.
- Route user-facing strings through `pdf_toolbox.i18n.tr`/`label` and update
  locale JSON files.
- Use the shared logging utilities; avoid `print` and ad-hoc loggers.

## Respect exception handling

- Inline exceptions must follow the repository format and appear in
  [DEVELOPMENT_EXCEPTIONS.md](../../DEVELOPMENT_EXCEPTIONS.md) via
  `scripts/generate_exception_overview.py`.
