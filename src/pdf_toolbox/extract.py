"""Compatibility wrapper for :mod:`pdf_toolbox.builtin.extract`."""

from pdf_toolbox.builtin.extract import *  # noqa: F403

if __name__ == "__main__":  # pragma: no cover - CLI passthrough
    import runpy

    runpy.run_module("pdf_toolbox.builtin.extract", run_name="__main__")
