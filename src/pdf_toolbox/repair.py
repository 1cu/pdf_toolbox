"""Compatibility wrapper for :mod:`pdf_toolbox.builtin.repair`."""

from pdf_toolbox.builtin.repair import *  # noqa: F403

if __name__ == "__main__":  # pragma: no cover - CLI passthrough
    import runpy

    runpy.run_module("pdf_toolbox.builtin.repair", run_name="__main__")
