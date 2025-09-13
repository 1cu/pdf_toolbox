# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e '.[dev]'`.
- Bump the `version` in `pyproject.toml` once per pull request, not for every commit.
- Install `pre-commit` hooks with `pre-commit install` so code is validated.
- Always run `pre-commit run --all-files` before committing changes.
- Export `QT_QPA_PLATFORM=offscreen` when running tests or pre-commit so Qt
  uses its headless backend.
- Let `pre-commit` finish even if it takes a while; security scans may need
  network access and can run for several minutes.
- Hook groups are separated by meta hooks and share aliases so you can run
  `pre-commit run format|lint|tests` to execute formatters, linters, or tests
  independently.
- Bandit handles static security checks; dependency vulnerability auditing is
  omitted because the project is not published on PyPI.
- If the run reformats files, stage the changes and re-run
  `pre-commit run --files <updated files>` to verify the hooks pass without
  reprocessing the entire repository. Subsequent runs are fast thanks to caching.
- Write descriptive commit messages: start with a short imperative summary
  (\<=72 characters), leave a blank line, then provide detailed context and
  rationale. Avoid generic messages like "fix tests".
- Maintain at least 95% test coverage for every module (excluding `pdf_toolbox/gui.py`).
  The `pre-commit` hook runs `pytest` with coverage and fails if any file falls below this threshold.
- Use `python -m build` to create distributions when publishing a release.
