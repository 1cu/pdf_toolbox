# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e '.[dev]'`.
- Bump the `version` in `pyproject.toml` when preparing pull requests.
- Install both pre-commit and commit-msg hooks with `pre-commit install --hook-type pre-commit --hook-type commit-msg` so code and commit messages are validated.
- Optionally customize gitlint rules by generating `~/.gitlint` with `gitlint generate-config`.
- Write descriptive commit messages: start with a short imperative summary
  (<=72 characters), leave a blank line, then provide detailed context and
  rationale. Avoid generic messages like "fix tests".
- Run `pre-commit run --all-files` and `pytest` before committing changes.
- Maintain at least 80% test coverage for every module (excluding `pdf_toolbox/gui.py`).
  The `pre-commit` hook runs `pytest` with coverage and fails if any file falls below this threshold.
- Use `python -m build` to create distributions when publishing a release.
