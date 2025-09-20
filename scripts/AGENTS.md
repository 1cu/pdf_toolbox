# Agent Rules for `scripts`

Follow the repository-wide [AGENTS.md](../AGENTS.md). Scripts should stay thin
wrappers around reusable library code. `scripts/pin_actions.py` is the planned
exception because it automates the workflow action pinning process.

## Structure scripts

- Provide a `main()` function and guard it with `if __name__ == "__main__":`.
- Accept arguments via `argparse` when needed; avoid ad-hoc parsing.
- Keep heavy logic in `src/pdf_toolbox` modules so it can be tested directly.

## Maintain quality

- Add type hints and concise docstrings to helper functions.
- Ensure scripts run with `python scripts/<name>.py` from the repository root.
- Respect the exception policy; run
  `python scripts/generate_exception_overview.py` to document any unavoidable
  inline disables.
