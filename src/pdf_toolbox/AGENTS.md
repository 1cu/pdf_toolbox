# Agent Guidelines for `src/pdf_toolbox`

- Use absolute imports; avoid relative imports.
- Provide module-level docstrings and detailed docstrings for all public
  classes and functions. Write them in Google style so `sphinx`/`autodoc`
  can render proper documentation.
- Apply type hints to all function and method signatures.
- Keep functions focused and small; extract helpers when logic grows.
- When functionality changes, add or update tests in `tests/`.
