# Agent Guidelines for `scripts`

- Scripts should be runnable with `python scripts/<name>.py`.
- Place logic in a `main()` function and guard execution with `if __name__ == "__main__": main()`.
- Use `argparse` for command-line arguments when needed.
- Prefer adding complex logic to `src/pdf_toolbox` and keep scripts thin.
- Include type hints and docstrings for any helper functions.
