"""Ensure module entry points invoke the GUI main function."""

import runpy
from types import ModuleType

import pytest

gui: ModuleType = pytest.importorskip("pdf_toolbox.gui")


def test_package_run_calls_gui_main(monkeypatch):
    called: list[bool] = []
    monkeypatch.setattr(gui, "main", lambda: called.append(True))
    runpy.run_module("pdf_toolbox", run_name="__main__")
    assert called


def test_gui_module_run_calls_main(monkeypatch):
    called: list[bool] = []
    monkeypatch.setattr(gui, "main", lambda: called.append(True))
    runpy.run_module("pdf_toolbox.gui", run_name="__main__")
    assert called
