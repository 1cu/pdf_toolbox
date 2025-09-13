"""Compatibility wrapper for :mod:`pdf_toolbox.builtin.unlock`."""

from pdf_toolbox.builtin.unlock import *  # noqa: F403

if __name__ == "__main__":  # pragma: no cover - CLI passthrough
    import runpy

    runpy.run_module("pdf_toolbox.builtin.unlock", run_name="__main__")
