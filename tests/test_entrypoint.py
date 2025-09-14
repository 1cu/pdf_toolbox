import importlib
import runpy
from types import ModuleType

import pytest

gui: ModuleType | None
try:
    gui = importlib.import_module("pdf_toolbox.gui")
except Exception:  # pragma: no cover  # pdf-toolbox: optional GUI deps | issue:-
    gui = None
    pytest.skip("pdf_toolbox.gui not available", allow_module_level=True)


def test_package_run_calls_gui_main(monkeypatch):
    assert gui is not None
    called = []
    monkeypatch.setattr(gui, "main", lambda: called.append(True))
    runpy.run_module("pdf_toolbox", run_name="__main__")
    assert called
