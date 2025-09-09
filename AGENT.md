# Agent Guidelines

- Ensure the virtual environment is activated and dependencies installed with `pip install -e .[dev]`.
- Install Git hooks with `pre-commit install`.
- Run `pre-commit run --all-files` and `pytest` before committing changes.
- Use `python -m build` to create distributions when publishing a release.
