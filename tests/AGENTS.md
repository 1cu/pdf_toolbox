# Agent Guidelines for `tests`

- Use `pytest`-style tests; name files and test functions starting with `test_`.
- Keep tests deterministic and isolated; use fixtures such as `tmp_path` for filesystem interactions.
- Prefer descriptive variable and fixture names.
- Reuse common fixtures when applicable to avoid duplication.
- Add tests for new features or bug fixes to maintain coverage targets.
