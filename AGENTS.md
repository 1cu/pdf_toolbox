# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e '.[dev]'`.
- Bump the `version` in `pyproject.toml` once per pull request, not for every commit.
- Install `pre-commit` hooks with `pre-commit install` so code is validated.
- Always run `pre-commit run --all-files` before committing changes.
- Write descriptive commit messages: start with a short imperative summary
  (\<=72 characters), leave a blank line, then provide detailed context and
  rationale. Avoid generic messages like "fix tests".
- Maintain at least 95% test coverage for every module (excluding `pdf_toolbox/gui.py`).
  The `pre-commit` hook runs `pytest` with coverage and fails if any file falls below this threshold.
- Use `python -m build` to create distributions when publishing a release.
