# Agent Rules for `tests`

Follow the repository-wide [AGENTS.md](../AGENTS.md). These additions keep the
test suite reliable and high-coverage.

## Write focused tests

- Use pytest naming (`test_*.py`, `test_*` functions).
- Keep tests deterministic. Use fixtures such as `tmp_path` and `monkeypatch`
  instead of relying on global state.
- Cover both success and failure paths for new functionality to protect the
  95% per-file coverage requirement.

## Use shared helpers

- Reuse fixtures from `conftest.py` and helper modules rather than duplicating
  setup logic.
- Avoid committing binary fixtures; generate PPTX/PDF assets on the fly.

## Handle exceptions properly

- Inline exceptions must follow the repository format and appear in
  [DEVELOPMENT_EXCEPTIONS.md](../DEVELOPMENT_EXCEPTIONS.md) via the generator
  script.
