# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e '.[dev]'`.
- Bump the `version` in `pyproject.toml` when preparing pull requests.
- Install Git hooks with `pre-commit install`.
- Run `pre-commit run --all-files` and `pytest` before committing changes.
- Maintain at least 80% test coverage for every module (excluding `pdf_toolbox/gui.py`).
  The `pre-commit` hook runs `pytest` with coverage and fails if any file falls below this threshold.
- Use `python -m build` to create distributions when publishing a release.
