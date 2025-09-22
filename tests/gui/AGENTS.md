# Agent Rules for `tests/gui`

These notes apply to all GUI-focused tests. Combine them with the repository
and `tests/` level rules.

## Coverage and scope

- Target ≥95% coverage for every GUI module so we can remove the coverage
  exceptions in `pyproject.toml`.
- Remove `# pragma: no cover` guards only after exercising each branch through a
  deterministic test.
- Prefer small, behaviour-driven tests that drive a single signal or widget
  method rather than end-to-end scenarios.

## Working with Qt

- Use `pytest.mark.gui` to keep GUI cases grouped and runnable via
  `pytest -m gui`.
- Always drive widgets through `qtbot`; rely on helpers such as
  `qtbot.waitUntil`, `qtbot.waitSignal`, and `QApplication.processEvents()`
  instead of `time.sleep`.
- Reuse fixtures from `conftest_qt.py` (`force_lang_en`, `temp_config_dir`,
  `no_file_dialogs`) and add new helpers there when you need to patch dialogs or
  worker threads. Avoid per-test monkeypatch pyramids.
- Stub dialogs (`QMessageBox`, `QDialog.exec`) and long-running workers via
  fixtures so that tests remain headless and synchronous.

## Test data and assertions

- Assert on both the UI state (visible text, enabled flags, `QAction` state) and
  the side effects (config updates, emitted signals).
- Use `qtbot.waitUntil` to observe log handler updates instead of poking at
  private attributes.
- Collect log output through the existing Qt log handler rather than matching on
  stdout/stderr.

Following these conventions will let us expand GUI coverage quickly without
sacrificing determinism.
