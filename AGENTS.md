# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e '.[dev]'`.
- Bump the `version` in `pyproject.toml` once per pull request, not for every commit.
- Install `pre-commit` hooks with `pre-commit install` so code is validated.
- Write descriptive commit messages: start with a short imperative summary
  (<=72 characters), leave a blank line, then provide detailed context and
  rationale. Avoid generic messages like "fix tests".
- Run `pre-commit run --all-files` before committing; it runs `pytest` automatically.
- Include the last 50 lines of `pre-commit` output in logs (e.g. `tail -n 50`).
- If `ruff format` rewrites files, rerun `pre-commit`; formatting itself is not a failure.
- Maintain at least 95% test coverage for every module (excluding `pdf_toolbox/gui.py`).
  The `pre-commit` hook runs `pytest` with coverage and fails if any file falls below this threshold.
- Use `python -m build` to create distributions when publishing a release.
